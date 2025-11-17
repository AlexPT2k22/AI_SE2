# main.py — FastAPI + Monitor de Estacionamento (CNN only + WebSocket)

from __future__ import annotations

from typing import Any, List, Dict, Optional, Tuple
import os
import cv2
import numpy as np
import json
from pathlib import Path
from collections import defaultdict, deque
import threading
import asyncio

import torch
from PIL import Image
import torchvision.transforms as T

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse

from spot_classifier import SpotClassifier


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "video.mp4")            # pode ser 0, ficheiro ou RTSP
SPOTS_FILE = Path(os.getenv("SPOTS_FILE", "parking_spots.json"))
MODEL_FILE = Path(os.getenv("MODEL_FILE", "spot_classifier.pth"))

DEVICE_NAME = os.getenv("DEVICE", "auto")                       # "cpu", "cuda" ou "auto"
SPOT_THRESHOLD = float(os.getenv("SPOT_THRESHOLD", 0.7))
HISTORY_LEN = int(os.getenv("HISTORY_LEN", 5))
PROCESS_EVERY_N_FRAMES = int(os.getenv("PROCESS_EVERY_N_FRAMES", 2))  # 1 em cada N frames
IMG_SIZE = 64


# ------------------------------------------------------------
# FASTAPI
# ------------------------------------------------------------
app = FastAPI()

# Estado global das vagas
g_spot_status: Dict[str, Any] = {}
g_lock = threading.Lock()

# Loop principal do FastAPI (para usar no thread)
event_loop: Optional[asyncio.AbstractEventLoop] = None


# ------------------------------------------------------------
# WebSocket Manager
# ------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = ConnectionManager()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def get_torch_device() -> torch.device:
    if DEVICE_NAME.lower() == "cpu":
        print("[INFO] Forçado a CPU")
        return torch.device("cpu")

    if torch.cuda.is_available():
        print("[INFO] Usando GPU (CUDA)")
        return torch.device("cuda")

    print("[INFO] Usando CPU (CUDA indisponível)")
    return torch.device("cpu")


def load_spots(spots_path: Path):
    if not spots_path.exists():
        raise FileNotFoundError(f"Spots não encontrados: {spots_path}")

    with open(spots_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    spots_raw = payload["spots"]
    result = []

    for s in spots_raw:
        pts = np.array([[p["x"], p["y"]] for p in s["points"]], dtype=np.float32)
        result.append({"name": s["name"], "points": pts})

    ref = payload.get("reference_size")
    reference_size = (
        (int(ref["width"]), int(ref["height"]))
        if ref else None
    )

    return result, reference_size


def scale_spots(spots, ref_size, frame_size):
    fw, fh = frame_size

    if ref_size:
        sx = fw / ref_size[0]
        sy = fh / ref_size[1]
        print(f"[INFO] Escala vagas: sx={sx:.3f}, sy={sy:.3f}")
    else:
        sx = sy = 1.0
        print("[WARN] reference_size ausente, assumindo escala 1:1")

    scaled = []
    for spot in spots:
        pts = spot["points"].copy()
        pts[:, 0] *= sx
        pts[:, 1] *= sy

        pts_int = np.round(pts).astype(np.int32)

        scaled.append({
            "name": spot["name"],
            "points": pts_int
        })

    return scaled


def build_batch(frame, scaled_spots, transform):
    h, w = frame.shape[:2]
    meta = []
    tensors = []

    for spot in scaled_spots:
        name = spot["name"]
        pts = spot["points"]

        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)

        cropped = cv2.bitwise_and(frame, frame, mask=mask)
        x, y, w_box, h_box = cv2.boundingRect(pts)
        crop = cropped[y:y + h_box, x:x + w_box]

        if crop.size == 0:
            continue

        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(crop)
        tensors.append(transform(img))
        meta.append((name, pts))

    if not tensors:
        return meta, None

    return meta, torch.stack(tensors, dim=0)


# ------------------------------------------------------------
# LOOP PRINCIPAL EM THREAD SEPARADA
# ------------------------------------------------------------
def parking_monitor_loop():
    global g_spot_status

    print("[INFO] Iniciando monitor de estacionamento...")

    # carregar modelo
    device = get_torch_device()
    model = SpotClassifier().to(device)
    model.load_state_dict(torch.load(MODEL_FILE, map_location=device))
    model.eval()

    # transform
    transform = T.Compose([
        T.Resize((IMG_SIZE, IMG_SIZE)),
        T.ToTensor(),
        T.Normalize([0.5]*3, [0.5]*3)
    ])

    # carregar vagas
    spots, ref = load_spots(SPOTS_FILE)

    # abrir vídeo / stream
    source_is_file = isinstance(VIDEO_SOURCE, str) and Path(VIDEO_SOURCE).is_file()
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print(f"[ERRO] Não abriu vídeo/stream: {VIDEO_SOURCE}")
        return

    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Vídeo: {fw}x{fh}")

    scaled_spots = scale_spots(spots, ref, (fw, fh))

    history = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
    frame_i = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            if source_is_file:
                print("[INFO] Reiniciando vídeo para loop.")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_i = 0
                continue
            print("[INFO] Fim do vídeo / stream terminou.")
            break

        frame_i += 1

        if frame_i % PROCESS_EVERY_N_FRAMES != 0:
            continue

        meta, batch = build_batch(frame, scaled_spots, transform)

        state: Dict[str, Any] = {}

        if batch is not None:
            batch = batch.to(device)
            with torch.no_grad():
                preds = model(batch)
                probs = torch.softmax(preds, dim=1).cpu().numpy()

            for i, (name, pts) in enumerate(meta):
                p_occ = float(probs[i][1])
                occ_raw = (p_occ >= SPOT_THRESHOLD)

                history[name].append(1 if occ_raw else 0)
                occ_final = (sum(history[name]) > len(history[name]) / 2)

                state[name] = {
                    "occupied": occ_final,
                    "prob": p_occ,
                }

        # atualizar estado global
        with g_lock:
            g_spot_status = state

        # broadcast via websocket
        if event_loop is not None:
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(state),
                event_loop
            )

    cap.release()
    print("[INFO] Monitor parado.")


# ------------------------------------------------------------
# FASTAPI ENDPOINTS
# ------------------------------------------------------------
@app.get("/parking")
def parking_status():
    with g_lock:
        return JSONResponse(g_spot_status)


@app.get("/")
def index():
    return HTMLResponse("""
    <html>
    <head>
    <title>Parking Monitor</title>
    <style>
        body { font-family: sans-serif; background: #111; color: #eee; }
        h1 { margin-bottom: 0.5rem; }
        #spots { display: flex; flex-wrap: wrap; gap: 10px; }
        .spot {
            padding: 10px 14px;
            border-radius: 8px;
            min-width: 180px;
            background: #222;
            box-shadow: 0 0 10px rgba(0,0,0,0.4);
        }
    </style>
    </head>
    <body>
        <h1>Estado das Vagas (WebSocket)</h1>
        <div id="spots">A ligar ao servidor...</div>

        <script>
        const spotsDiv = document.getElementById("spots");
        const ws = new WebSocket("ws://" + location.host + "/ws");

        ws.onopen = () => {
            spotsDiv.innerHTML = "À espera de dados...";
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            spotsDiv.innerHTML = "";

            const names = Object.keys(data).sort();

            if (names.length === 0) {
                spotsDiv.innerHTML = "Sem dados de vagas ainda.";
                return;
            }

            for (const name of names) {
                const s = document.createElement("div");
                s.className = "spot";
                const occ = data[name].occupied;
                const prob = data[name].prob.toFixed(2);
                s.style.background = occ ? "#b00020" : "#006400";
                s.innerText = name + " — " + (occ ? "OCUPADO" : "LIVRE") + " (" + prob + ")";
                spotsDiv.appendChild(s);
            }
        };

        ws.onerror = (e) => {
            console.error("WebSocket error", e);
        };

        ws.onclose = () => {
            spotsDiv.innerHTML = "Ligação WebSocket fechada.";
        };
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # não esperamos nada do cliente; só mantemos a ligação aberta
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ------------------------------------------------------------
# STARTUP: arrancar thread + apanhar event loop
# ------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    global event_loop
    event_loop = asyncio.get_running_loop()
    t = threading.Thread(target=parking_monitor_loop, daemon=True)
    t.start()
    print("[INFO] Thread de monitorização iniciada.")
