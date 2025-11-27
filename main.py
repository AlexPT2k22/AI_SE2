# main.py â€” FastAPI + Monitor de Estacionamento (CNN only + WebSocket)

from __future__ import annotations

from typing import Any, List, Dict, Optional, Tuple, Sequence
import os
import cv2
import numpy as np
import json
from pathlib import Path
from collections import defaultdict, deque
import threading
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

import torch
from PIL import Image
import torchvision.transforms as T
import asyncpg
from asyncpg import exceptions as pg_exceptions

try:
    from fast_alpr import ALPR  # type: ignore
except ImportError:  # pragma: no cover - fallback when package missing
    ALPR = None

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from spot_classifier import SpotClassifier

try:
    from supabaseStorage import SupabaseStorageService
except ImportError:
    SupabaseStorageService = None


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
IMG_SIZE = 64  # tamanho da imagem de input para a CNN
PARKING_RATE_PER_HOUR = float(os.getenv("PARKING_RATE_PER_HOUR", 1.50))  # tarifa por hora

def _str_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_providers(value: str) -> List[str]:
    if not value:
        return []
    providers = [p.strip() for p in value.split(",")]
    return [p for p in providers if p]


ENABLE_ALPR = _str_to_bool(os.getenv("ENABLE_ALPR", "true"))
ALPR_DETECTOR_MODEL = os.getenv("ALPR_DETECTOR_MODEL", "yolo-v9-s-608-license-plate-end2end")
ALPR_OCR_MODEL = os.getenv("ALPR_OCR_MODEL", "cct-s-v1-global-model")
ALPR_WORKERS = max(1, int(os.getenv("ALPR_WORKERS", "1")))
ALPR_EVENT_BUFFER = int(os.getenv("ALPR_EVENT_BUFFER", "40"))
ALPR_DETECTOR_PROVIDERS = _parse_providers(os.getenv("ALPR_DETECTOR_PROVIDERS", "CPUExecutionProvider"))
ALPR_OCR_PROVIDERS = _parse_providers(os.getenv("ALPR_OCR_PROVIDERS", "CPUExecutionProvider"))
ALPR_OCR_DEVICE = os.getenv("ALPR_OCR_DEVICE", "cpu")
DEFAULT_RESERVATION_HOURS = float(os.getenv("RESERVATION_HOURS", "24"))
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-me")
DATABASE_URL = os.getenv("DATABASE_URL")

# Supabase Storage Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "parking-images")
SUPABASE_PUBLIC_BUCKET = _str_to_bool(os.getenv("SUPABASE_PUBLIC_BUCKET", "false"))

if ENABLE_ALPR and ALPR is None:
    print("[WARN] fast_alpr nao encontrado; ALPR desativado.")
    ENABLE_ALPR = False


# ------------------------------------------------------------
# FASTAPI
# ------------------------------------------------------------
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=7 * 24 * 3600)

# Estado global das vagas
g_spot_status: Dict[str, Any] = {}
g_spot_meta: Dict[str, Dict[str, Any]] = {}
g_lock = threading.Lock()
g_frame_lock = threading.Lock()
g_last_frame_jpeg: Optional[bytes] = None
g_plate_lock = threading.Lock()
g_plate_memory: Dict[str, Dict[str, Any]] = {}
g_plate_events: deque = deque(maxlen=ALPR_EVENT_BUFFER)
g_plate_events_lock = threading.Lock()
g_alpr_pending_lock = threading.Lock()
g_alpr_pending = set()
g_reservations_lock = threading.Lock()
g_active_reservations: Dict[str, Dict[str, Any]] = {}
g_users_lock = threading.Lock()
g_users: Dict[str, Dict[str, Any]] = {}
db_pool: Optional[asyncpg.Pool] = None

# Supabase Storage Service
supabase_storage: Optional[SupabaseStorageService] = None
if SupabaseStorageService and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_storage = SupabaseStorageService(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY,
            bucket_name=SUPABASE_BUCKET,
            public_bucket=SUPABASE_PUBLIC_BUCKET,
        )
        print(f"[INFO] Supabase Storage inicializado: bucket '{SUPABASE_BUCKET}'")
    except Exception as e:
        print(f"[WARN] Falha ao inicializar Supabase Storage: {e}")
        supabase_storage = None


alpr_executor: Optional[ThreadPoolExecutor] = ThreadPoolExecutor(max_workers=ALPR_WORKERS) if ENABLE_ALPR else None
_alpr_instance_lock = threading.Lock()
_alpr_instance: Optional["ALPR"] = None

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
        print("[INFO] ForÃ§ado a CPU")
        return torch.device("cpu")

    if torch.cuda.is_available():
        print("[INFO] Usando GPU (CUDA)")
        return torch.device("cuda")

    print("[INFO] Usando CPU (CUDA indisponÃ­vel)")
    return torch.device("cpu")


def load_spots(spots_path: Path):
    if not spots_path.exists():
        raise FileNotFoundError(f"Spots nÃ£o encontrados: {spots_path}")

    with open(spots_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    spots_raw = payload["spots"]
    result = []

    for s in spots_raw:
        pts = np.array([[p["x"], p["y"]] for p in s["points"]], dtype=np.float32)
        result.append({
            "name": s["name"],
            "points": pts,
            "reserved": bool(s.get("reserved", False)),
            "authorized": s.get("authorized_plates", []) or [],
        })

    ref = payload.get("reference_size")
    reference_size = (
        (int(ref["width"]), int(ref["height"]))
        if ref else None
    )

    return result, reference_size


def update_spot_meta_cache(spots: List[Dict[str, Any]]):
    global g_spot_meta
    g_spot_meta = {
        spot["name"]: {
            "reserved": bool(spot.get("reserved", False)),
            "authorized": list(spot.get("authorized", []) or []),
        }
        for spot in spots
    }


def ensure_spot_meta_loaded():
    if g_spot_meta:
        return
    if not SPOTS_FILE.exists():
        return
    try:
        spots, _ = load_spots(SPOTS_FILE)
    except Exception:
        return
    update_spot_meta_cache(spots)


def resolve_spot_name(raw: str) -> Optional[str]:
    if not raw:
        return None
    ensure_spot_meta_loaded()
    target = raw.strip()
    if not target:
        return None
    if target in g_spot_meta:
        return target
    lower = target.lower()
    for name in g_spot_meta.keys():
        if name.lower() == lower:
            return name
    return None


async def refresh_users_cache() -> List[Dict[str, Any]]:
    if not db_pool:
        with g_users_lock:
            return [
                {"name": info["name"], "plate": info["plate"], "plate_norm": info["plate_norm"]}
                for info in g_users.values()
            ]
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT full_name, plate, plate_norm FROM public.parking_web_users"
        )
    payload = [
        {"name": row["full_name"], "plate": row["plate"], "plate_norm": row["plate_norm"]}
        for row in rows
    ]
    with g_users_lock:
        g_users.clear()
        for row in payload:
            g_users[row["plate_norm"]] = dict(row)
    return payload


async def refresh_reservations_cache() -> List[Dict[str, Any]]:
    if not db_pool:
        with g_reservations_lock:
            return [
                {
                    "spot": spot,
                    "plate": info.get("plate_raw"),
                    "expires_at": info.get("expires_at"),
                    "reserved_by": info.get("reserved_by"),
                }
                for spot, info in g_active_reservations.items()
            ]
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM public.parking_manual_reservations WHERE reserved_until <= NOW()"
        )
        rows = await conn.fetch(
            "SELECT spot, plate, plate_norm, reserved_by, reserved_until, created_at "
            "FROM public.parking_manual_reservations"
        )
    result: List[Dict[str, Any]] = []
    with g_reservations_lock:
        g_active_reservations.clear()
        for row in rows:
            expires_at = row["reserved_until"].timestamp()
            entry = {
                "spot": row["spot"],
                "plate": row["plate"],
                "plate_norm": row["plate_norm"],
                "reserved_by": row["reserved_by"],
                "created_at": row["created_at"].timestamp() if row["created_at"] else None,
                "expires_at": expires_at,
            }
            g_active_reservations[row["spot"]] = {
                "plate_raw": row["plate"],
                "plate_norm": row["plate_norm"],
                "reserved_by": row["reserved_by"],
                "created_at": entry["created_at"],
                "expires_at": expires_at,
            }
            result.append(entry)
    return result


async def db_delete_reservations(spots: Sequence[str]):
    if not db_pool or not spots:
        return
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM public.parking_manual_reservations WHERE spot = ANY($1::text[])",
            list(spots),
        )
    await refresh_reservations_cache()


async def ensure_user_loaded(plate_norm: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_plate_norm(plate_norm)
    if user:
        return user
    if not db_pool:
        return None
    await refresh_users_cache()
    return get_user_by_plate_norm(plate_norm)


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
            "points": pts_int,
            "reserved": bool(spot.get("reserved", False)),
            "authorized": spot.get("authorized", []) or [],
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


def get_alpr_instance() -> Optional["ALPR"]:
    if not ENABLE_ALPR or ALPR is None:
        return None
    global _alpr_instance
    if _alpr_instance is not None:
        return _alpr_instance

    with _alpr_instance_lock:
        if _alpr_instance is not None:
            return _alpr_instance
        try:
            print("[INFO] Inicializando ALPR...")
            _alpr_instance = ALPR(
                detector_model=ALPR_DETECTOR_MODEL,
                ocr_model=ALPR_OCR_MODEL,
                detector_providers=ALPR_DETECTOR_PROVIDERS or None,
                ocr_providers=ALPR_OCR_PROVIDERS or None,
                ocr_device=ALPR_OCR_DEVICE,
            )
        except Exception as exc:  # pragma: no cover - falha de inicializaï¿½ï¿½o
            print(f"[WARN] Falha ao inicializar ALPR: {exc}")
            return None
    return _alpr_instance


def _normalize_confidence(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple)):
        vals = [float(v) for v in value if v is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)
    return None


def normalize_plate_text(plate: Optional[str]) -> Optional[str]:
    if not plate:
        return None
    filtered = "".join(ch for ch in plate.upper() if ch.isalnum())
    return filtered or None


def get_user_by_plate_norm(plate_norm: str) -> Optional[Dict[str, Any]]:
    with g_users_lock:
        info = g_users.get(plate_norm)
        return dict(info) if info else None


def get_session_user(request: Request) -> Optional[Dict[str, Any]]:
    user = request.session.get("user")
    if not user:
        return None
    return user


def prune_expired_reservations():
    now = time.time()
    expired: List[str] = []
    with g_reservations_lock:
        for spot, info in list(g_active_reservations.items()):
            if info.get("expires_at", 0) <= now:
                expired.append(spot)
                g_active_reservations.pop(spot, None)
    if expired and db_pool and event_loop:
        asyncio.run_coroutine_threadsafe(db_delete_reservations(expired), event_loop)


def get_reservation_info(name: str) -> Optional[Dict[str, Any]]:
    prune_expired_reservations()
    with g_reservations_lock:
        info = g_active_reservations.get(name)
        return dict(info) if info else None


def extract_spot_crop(frame: np.ndarray, pts: np.ndarray) -> Optional[np.ndarray]:
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    x, y, w, h = cv2.boundingRect(pts)
    if w <= 0 or h <= 0:
        return None
    roi = cv2.bitwise_and(frame, frame, mask=mask)
    crop = roi[y:y + h, x:x + w]
    if crop.size == 0:
        return None
    return crop.copy()


def _run_alpr_job(name: str, crop: np.ndarray):
    alpr = get_alpr_instance()
    if alpr is None:
        return name, None
    try:
        results = alpr.predict(crop)
    except Exception as exc:
        print(f"[WARN] ALPR falhou para {name}: {exc}")
        return name, None

    if not results:
        return name, None

    first = results[0] if isinstance(results, (list, tuple)) else results
    plate = getattr(first.ocr, "text", None) if getattr(first, "ocr", None) else None
    ocr_conf = (
        _normalize_confidence(getattr(first.ocr, "confidence", None))
        if getattr(first, "ocr", None) else None
    )
    det_conf = (
        _normalize_confidence(getattr(first.detection, "confidence", None))
        if getattr(first, "detection", None) else None
    )

    event = {
        "spot": name,
        "plate": plate,
        "ocr_conf": ocr_conf,
        "det_conf": det_conf,
        "timestamp": time.time(),
    }
    return name, event


def _handle_alpr_future(future: Future):
    try:
        name, event = future.result()
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] ALPR future erro: {exc}")
        return
    finally:
        with g_alpr_pending_lock:
            g_alpr_pending.discard(name)

    if not event or not event.get("plate"):
        return

    meta = g_spot_meta.get(name, {})
    base_reserved = bool(meta.get("reserved", False))
    authorized = meta.get("authorized", []) or []
    allowed = {normalize_plate_text(p) for p in authorized if normalize_plate_text(p)}
    reservation_info = get_reservation_info(name)
    reserved = bool(base_reserved or reservation_info)
    if reservation_info and reservation_info.get("plate_norm"):
        allowed.add(reservation_info["plate_norm"])

    plate_norm = normalize_plate_text(event["plate"])
    violation = bool(
        reserved and allowed and (not plate_norm or plate_norm not in allowed)
    )
    event["reserved"] = reserved
    event["violation"] = violation
    event["authorized"] = authorized
    if reservation_info:
        event["reservation"] = {
            "expires_at": reservation_info.get("expires_at"),
            "plate": reservation_info.get("plate_raw"),
        }

    with g_plate_lock:
        g_plate_memory[event["spot"]] = {
            "plate": event["plate"],
            "ocr_conf": event.get("ocr_conf"),
            "det_conf": event.get("det_conf"),
            "timestamp": event.get("timestamp"),
            "violation": violation,
            "reserved": reserved,
            "reservation": event.get("reservation"),
        }

    with g_plate_events_lock:
        g_plate_events.appendleft(event)

    with g_lock:
        spot_state = g_spot_status.get(name)
        if spot_state is not None:
            spot_state["plate"] = event["plate"]
            spot_state["plate_conf"] = event.get("ocr_conf")
            spot_state["plate_timestamp"] = event.get("timestamp")
            spot_state["violation"] = violation
            spot_state["reserved"] = reserved
            if event.get("reservation") is not None:
                spot_state["reservation"] = event.get("reservation")
            snapshot = {k: dict(v) for k, v in g_spot_status.items()}
        else:
            snapshot = None

    if snapshot and event_loop is not None:
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast(snapshot),
            event_loop
        )


def schedule_alpr(name: str, crop: Optional[np.ndarray]):
    if not ENABLE_ALPR or crop is None or alpr_executor is None:
        return
    with g_alpr_pending_lock:
        if name in g_alpr_pending:
            return
        g_alpr_pending.add(name)
    future = alpr_executor.submit(_run_alpr_job, name, crop)
    future.add_done_callback(_handle_alpr_future)


def clear_plate_for_spot(name: str):
    with g_plate_lock:
        g_plate_memory.pop(name, None)
    with g_alpr_pending_lock:
        g_alpr_pending.discard(name)


def annotate_frame(frame: np.ndarray, scaled_spots, state: Dict[str, Any]) -> np.ndarray:
    overlay = frame.copy()

    for spot in scaled_spots:
        pts = spot["points"]
        info = state.get(spot["name"], {})
        occupied = info.get("occupied", False)
        prob = info.get("prob", 0.0)
        reserved = spot.get("reserved", False) or info.get("reserved", False)
        violation = info.get("violation", False)
        plate = info.get("plate")
        reservation_meta = info.get("reservation") or {}

        if violation:
            fill_color = (0, 0, 255)
            border_color = (0, 0, 180)
        elif reserved:
            if occupied:
                fill_color = (255, 0, 0)   # blue (BGR)
                border_color = (255, 120, 120)
            else:
                fill_color = (200, 150, 50)
                border_color = (220, 180, 120)
        else:
            fill_color = (0, 0, 180) if occupied else (0, 160, 0)
            border_color = (0, 0, 255) if occupied else (0, 255, 0)

        cv2.fillPoly(overlay, [pts], fill_color)
        cv2.polylines(overlay, [pts], True, border_color, 2)

        centroid = np.mean(pts, axis=0).astype(int)
        label = f"{spot['name']} ({prob:.2f})" if prob else str(spot["name"])
        tags = []
        if reserved:
            tags.append("R")
        if violation:
            tags.append("VIOL")
        if tags:
            label += " [" + ",".join(tags) + "]"
        if plate:
            label += f" {plate}"
        res_plate = reservation_meta.get("plate")
        if res_plate:
            label += f" @({res_plate})"
        cv2.putText(
            overlay,
            label,
            (int(centroid[0] - 20), int(centroid[1])),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    annotated = cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)
    return annotated


def store_frame(frame: np.ndarray):
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return
    data = buf.tobytes()
    with g_frame_lock:
        global g_last_frame_jpeg
        g_last_frame_jpeg = data


# ------------------------------------------------------------
# LOOP PRINCIPAL EM THREAD SEPARADA
# ------------------------------------------------------------
def parking_monitor_loop():
    global g_spot_status, g_spot_meta

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
    update_spot_meta_cache(spots)

    # abrir vÃ­deo / stream
    source_is_file = isinstance(VIDEO_SOURCE, str) and Path(VIDEO_SOURCE).is_file()
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print(f"[ERRO] NÃ£o abriu vÃ­deo/stream: {VIDEO_SOURCE}")
        return

    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] VÃ­deo: {fw}x{fh}")

    scaled_spots = scale_spots(spots, ref, (fw, fh))
    spot_lookup = {spot["name"]: spot for spot in scaled_spots}

    history = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
    frame_i = 0
    current_state: Dict[str, Any] = {}
    last_occupancy: Dict[str, bool] = {spot["name"]: False for spot in scaled_spots}

    while True:
        ret, frame = cap.read()
        if not ret:
            if source_is_file:
                print("[INFO] Reiniciando vÃ­deo para loop.")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_i = 0
                continue
            print("[INFO] Fim do vÃ­deo / stream terminou.")
            break

        frame_i += 1

        recompute = (frame_i == 1) or (frame_i % PROCESS_EVERY_N_FRAMES == 0)

        if recompute:
            prune_expired_reservations()
            with g_reservations_lock:
                reservations_snapshot = {
                    spot: dict(info) for spot, info in g_active_reservations.items()
                }

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

                    spot_meta = spot_lookup.get(name, {})
                    reservation_info = reservations_snapshot.get(name)
                    is_reserved = bool(spot_meta.get("reserved", False) or reservation_info)

                    state[name] = {
                        "occupied": occ_final,
                        "prob": p_occ,
                        "reserved": is_reserved,
                        "authorized": list(spot_meta.get("authorized", []) or []),
                        "violation": False,
                    }
                    if reservation_info:
                        state[name]["reservation"] = {
                            "expires_at": reservation_info.get("expires_at"),
                            "plate": reservation_info.get("plate_raw"),
                        }
                    else:
                        state[name]["reservation"] = None

                    with g_plate_lock:
                        plate_info = g_plate_memory.get(name)
                    if plate_info:
                        state[name]["plate"] = plate_info.get("plate")
                        state[name]["plate_conf"] = plate_info.get("ocr_conf")
                        state[name]["plate_timestamp"] = plate_info.get("timestamp")
                        state[name]["violation"] = bool(plate_info.get("violation"))
                    else:
                        state[name]["plate"] = None
                        state[name]["plate_conf"] = None
                        state[name]["plate_timestamp"] = None
                        state[name]["violation"] = False

                    prev_occ = last_occupancy.get(name, False)
                    if occ_final and not prev_occ:
                        crop_pts = spot_lookup.get(name, {}).get("points", pts)
                        crop = extract_spot_crop(frame, crop_pts)
                        if is_reserved:
                            schedule_alpr(name, crop)
                    elif not occ_final:
                        clear_plate_for_spot(name)
                    last_occupancy[name] = occ_final

            current_state = state

            # atualizar estado global
            with g_lock:
                g_spot_status = current_state

            # broadcast via websocket
            if event_loop is not None:
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast(current_state),
                    event_loop
                )

        annotated = annotate_frame(frame, scaled_spots, current_state)
        store_frame(annotated)

    cap.release()
    print("[INFO] Monitor parado.")


# ------------------------------------------------------------
# FASTAPI ENDPOINTS
# ------------------------------------------------------------
@app.get("/parking")
def parking_status():
    with g_lock:
        return JSONResponse(g_spot_status)


@app.get("/video_feed")
async def video_feed():
    async def frame_generator():
        while True:
            with g_frame_lock:
                frame = g_last_frame_jpeg
            if frame is None:
                await asyncio.sleep(0.05)
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/plate_events")
def plate_events():
    with g_plate_events_lock:
        events = list(g_plate_events)
    return JSONResponse(events)


class ReservationPayload(BaseModel):
    spot: str = Field(..., min_length=1)
    hours: Optional[float] = Field(default=None, gt=0)


class AuthPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    plate: str = Field(..., min_length=1, max_length=32)

class EntryPayload(BaseModel):
    plate: str = Field(..., min_length=1, max_length=32)
    camera_id: str = Field(..., min_length=1)


class ExitPayload(BaseModel):
    plate: str = Field(..., min_length=1, max_length=32)
    camera_id: str = Field(..., min_length=1)


class PaymentPayload(BaseModel):
    session_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    method: str = Field(..., pattern="^(card|cash|mbway)$")


@app.get("/api/reservations")
async def list_reservations():
    records = await refresh_reservations_cache()
    if not records and not db_pool:
        prune_expired_reservations()
        with g_reservations_lock:
            records = [
                {
                    "spot": spot,
                    "plate": info.get("plate_raw"),
                    "expires_at": info.get("expires_at"),
                    "created_at": info.get("created_at"),
                }
                for spot, info in g_active_reservations.items()
            ]
    return JSONResponse(records)


@app.post("/api/reservations")
async def create_reservation(payload: ReservationPayload, request: Request):
    ensure_spot_meta_loaded()
    spot_name = resolve_spot_name(payload.spot)
    if spot_name is None:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Nao autenticado.")
    plate_value = user.get("plate")
    if not plate_value:
        raise HTTPException(status_code=400, detail="Perfil sem placa.")
    meta = g_spot_meta.get(spot_name, {})
    if meta.get("reserved"):
        raise HTTPException(status_code=400, detail="Esta vaga ja esta reservada permanentemente.")

    with g_lock:
        spot_state = g_spot_status.get(spot_name)
    if spot_state and spot_state.get("occupied"):
        raise HTTPException(status_code=400, detail="Nao e possivel reservar uma vaga ocupada.")

    prune_expired_reservations()

    duration = payload.hours if payload.hours and payload.hours > 0 else DEFAULT_RESERVATION_HOURS
    expires_at = time.time() + duration * 3600
    plate_norm = normalize_plate_text(plate_value)

    with g_reservations_lock:
        if spot_name in g_active_reservations:
            raise HTTPException(status_code=409, detail="Esta vaga ja possui uma reserva ativa.")

    if db_pool:
        expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        async with db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO public.parking_manual_reservations
                        (spot, plate, plate_norm, reserved_by, reserved_until)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    spot_name,
                    plate_value,
                    plate_norm,
                    user.get("name"),
                    expires_dt,
                )
            except pg_exceptions.UniqueViolationError:
                raise HTTPException(status_code=409, detail="Esta vaga ja possui uma reserva ativa.")
        await refresh_reservations_cache()
    else:
        with g_reservations_lock:
            g_active_reservations[spot_name] = {
                "plate_raw": plate_value,
                "plate_norm": plate_norm,
                "reserved_by": user.get("name"),
                "created_at": time.time(),
                "expires_at": expires_at,
            }

    return JSONResponse({"spot": spot_name, "plate": plate_value, "expires_at": expires_at})


@app.delete("/api/reservations/{spot}")
async def delete_reservation(spot: str):
    ensure_spot_meta_loaded()
    spot_name = resolve_spot_name(spot)
    if spot_name is None:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")
    if db_pool:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM public.parking_manual_reservations WHERE spot = $1",
                spot_name,
            )
        if result.split()[-1] == "0":
            raise HTTPException(status_code=404, detail="Reserva nao encontrada")
        await refresh_reservations_cache()
    else:
        with g_reservations_lock:
            info = g_active_reservations.pop(spot_name, None)
        if info is None:
            raise HTTPException(status_code=404, detail="Reserva nao encontrada")
    return JSONResponse({"spot": spot_name, "released": True})


@app.post("/api/auth/register")
async def auth_register(payload: AuthPayload, request: Request):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponivel.")
    name = payload.name.strip()
    plate = payload.plate.strip()
    plate_norm = normalize_plate_text(plate)
    if not name or not plate_norm:
        raise HTTPException(status_code=400, detail="Nome e placa validos sao obrigatorios.")
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO public.parking_web_users (full_name, plate, plate_norm)
                VALUES ($1, $2, $3)
                RETURNING full_name, plate, plate_norm
                """,
                name,
                plate,
                plate_norm,
            )
    except pg_exceptions.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Placa ja registada.")
    await refresh_users_cache()
    request.session["user"] = {"name": row["full_name"], "plate": row["plate"], "plate_norm": row["plate_norm"]}
    return {"name": row["full_name"], "plate": row["plate"]}


@app.post("/api/auth/login")
async def auth_login(payload: AuthPayload, request: Request):
    plate_norm = normalize_plate_text(payload.plate)
    if not plate_norm:
        raise HTTPException(status_code=400, detail="Placa invalida.")
    user = await ensure_user_loaded(plate_norm)
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador nao encontrado.")
    if user["name"].strip().lower() != payload.name.strip().lower():
        raise HTTPException(status_code=401, detail="Nome nao confere com a placa.")
    request.session["user"] = {"name": user["name"], "plate": user["plate"], "plate_norm": user["plate_norm"]}
    return {"name": user["name"], "plate": user["plate"]}


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    request.session.clear()
    response = JSONResponse({"ok": True})
    response.delete_cookie("session")
    return response


@app.get("/api/auth/me")
def auth_me(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Nao autenticado.")
    return user


# ------------------------------------------------------------
# Função auxiliar para processar imagem e detectar matrícula
# ------------------------------------------------------------
async def process_plate_image(image_bytes: bytes) -> Optional[str]:
    """
    Processa uma imagem e extrai a matrícula usando fast-alpr.
    Retorna a matrícula detectada ou None se não detectar nada.
    """
    try:
        # Converter bytes para numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None
        
        # Obter instância ALPR
        alpr = get_alpr_instance()
        if alpr is None:
            return None
        
        # Executar detecção
        results = alpr.predict(img)
        
        if not results:
            return None
        
        # Pegar o primeiro resultado
        first = results[0] if isinstance(results, (list, tuple)) else results
        plate_text = getattr(first.ocr, "text", None) if getattr(first, "ocr", None) else None
        
        return plate_text
        
    except Exception as e:
        print(f"[ERRO] Falha ao processar imagem ALPR: {e}")
        return None


@app.post("/api/entry")
async def api_entry(camera_id: str = Form(...), image: UploadFile = File(...)):
    """
    Registra entrada de veículo.
    Recebe imagem da matrícula do ESP32 e usa ALPR para detectar a placa.
    """
    if not camera_id:
        raise HTTPException(status_code=400, detail="camera_id obrigatório.")
    
    # Ler imagem
    image_bytes = await image.read()
    
    # Processar com ALPR
    plate = await process_plate_image(image_bytes)
    
    if not plate:
        raise HTTPException(status_code=400, detail="Nenhuma matricula detectada na imagem.")
    
    if db_pool:
        async with db_pool.acquire() as conn:
            # Verificar se já existe uma sessão aberta para esta matrícula
            existing_session = await conn.fetchrow(
                """
                SELECT id, entry_time, camera_id
                FROM public.parking_sessions
                WHERE plate = $1 AND status = 'open'
                ORDER BY entry_time DESC
                LIMIT 1
                """,
                plate,
            )
            
            if existing_session:
                # Já existe sessão aberta - NÃO faz upload da imagem
                return JSONResponse({
                    "session_id": existing_session["id"],
                    "entry_time": existing_session["entry_time"].isoformat(),
                    "plate": plate,
                    "camera_id": existing_session["camera_id"],
                    "duplicate": True,
                    "message": "Veiculo ja tem uma sessao aberta. Retornando sessao existente."
                })
            
            # Não existe sessão aberta - fazer upload da imagem AGORA
            image_url = None
            if supabase_storage:
                try:
                    image_url = supabase_storage.upload_and_get_url(
                        image_bytes=image_bytes,
                        plate=plate,
                        expires_in=365 * 24 * 3600,  # 1 ano
                        ext="jpg"
                    )
                    print(f"[INFO] Imagem uploaded: {image_url}")
                except Exception as e:
                    print(f"[WARN] Falha ao fazer upload da imagem: {e}")
                    # Não bloqueia o fluxo caso falhe o upload
            
            # Criar nova entrada com a URL da imagem
            row = await conn.fetchrow(
                """
                INSERT INTO public.parking_sessions (plate, camera_id, status, entry_image_url)
                VALUES ($1, $2, 'open', $3)
                RETURNING id, entry_time
                """,
                plate,
                camera_id,
                image_url,
            )
        return JSONResponse({
            "session_id": row["id"],
            "entry_time": row["entry_time"].isoformat(),
            "plate": plate,
            "camera_id": camera_id,
            "duplicate": False,
        })
    else:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")


@app.post("/api/exit")
async def api_exit(camera_id: str = Form(...), image: UploadFile = File(...)):
    """
    Registra saída de veículo.
    Recebe imagem da matrícula do ESP32 e usa ALPR para detectar a placa.
    """
    if not camera_id:
        raise HTTPException(status_code=400, detail="camera_id obrigatório.")
    
    # Ler imagem
    image_bytes = await image.read()
    
    # Processar com ALPR
    plate = await process_plate_image(image_bytes)
    
    if not plate:
        raise HTTPException(status_code=400, detail="Nenhuma matricula detectada na imagem.")
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")
    
    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT id, entry_time, exit_time, status
            FROM public.parking_sessions
            WHERE plate = $1 AND status = 'open'
            ORDER BY entry_time DESC
            LIMIT 1
            """,
            plate,
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Nenhuma sessao aberta encontrada para esta placa.")
        
        # Verificar se já tem saída registrada (prevenção de dupla saída)
        if session["exit_time"] is not None:
            return JSONResponse({
                "session_id": session["id"],
                "plate": plate,
                "duplicate": True,
                "message": "Saida ja registrada para esta sessao.",
                "exit_time": session["exit_time"].isoformat(),
            })
        
        session_id = session["id"]
        entry_time = session["entry_time"]
        exit_time = datetime.now(tz=timezone.utc)
        
        duration_seconds = (exit_time - entry_time).total_seconds()
        duration_hours = duration_seconds / 3600.0
        amount_due = round(duration_hours * PARKING_RATE_PER_HOUR, 2)
        
        # Upload da imagem de saída para Supabase
        exit_image_url = None
        if supabase_storage:
            try:
                exit_image_url = supabase_storage.upload_and_get_url(
                    image_bytes=image_bytes,
                    plate=f"{plate}/exit",  # Pasta separada para saídas
                    expires_in=365 * 24 * 3600,  # 1 ano
                    ext="jpg"
                )
                print(f"[INFO] Imagem de saída uploaded: {exit_image_url}")
            except Exception as e:
                print(f"[WARN] Falha ao fazer upload da imagem de saída: {e}")
        
        # Atualizar sessão com saída e marcar como 'paid' (fechar sessão)
        await conn.execute(
            """
            UPDATE public.parking_sessions
            SET exit_time = $1, amount_due = $2, status = 'paid', exit_image_url = $3
            WHERE id = $4
            """,
            exit_time,
            amount_due,
            exit_image_url,
            session_id,
        )
    
    return JSONResponse({
        "session_id": session_id,
        "plate": plate,
        "entry_time": entry_time.isoformat(),
        "exit_time": exit_time.isoformat(),
        "amount_due": amount_due,
        "camera_id": camera_id,
    })



@app.post("/api/payments")
async def api_payments(payload: PaymentPayload):
    session_id = payload.session_id
    amount = round(payload.amount, 2)
    method = payload.method
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")
    
    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT id, amount_due, amount_paid, status
            FROM public.parking_sessions
            WHERE id = $1
            """,
            session_id,
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
        
        await conn.execute(
            """
            INSERT INTO public.parking_payments (session_id, amount, method)
            VALUES ($1, $2, $3)
            """,
            session_id,
            amount,
            method,
        )
        
        current_paid = session["amount_paid"] or 0
        new_paid = round(current_paid + amount, 2)
        amount_due = session["amount_due"] or 0
        
        new_status = 'paid' if new_paid >= amount_due else session["status"]
        
        await conn.execute(
            """
            UPDATE public.parking_sessions
            SET amount_paid = $1, status = $2
            WHERE id = $3
            """,
            new_paid,
            new_status,
            session_id,
        )
    
    return JSONResponse({
        "session_id": session_id,
        "amount_paid": new_paid,
        "amount_due": amount_due,
        "status": new_status,
        "payment_method": method,
        "payment_amount": amount,
    })


@app.get("/")
def index():
    return HTMLResponse("""
    <html>
    <head>
    <title>Parking Monitor</title>
    <style>
        body { font-family: sans-serif; background: #0f1115; color: #f2f2f2; display: flex; align-items: center; justify-content: center; height: 100vh; margin:0; }
        .card { background: #1b1e24; padding: 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.5); text-align: center; }
        a { color: #3a8ef6; text-decoration: none; font-weight: bold; }
        ul { list-style: none; padding: 0; margin: 20px 0 0 0; }
        li { margin-bottom: 10px; }
    </style>
    </head>
    <body>
        <div class="card">
            <h1>Parking Monitor</h1>
            <p>Escolha uma opção:</p>
            <ul>
                <li><a href="/live">Ver monitor ao vivo</a></li>
                <li><a href="/reservations">Reservar vagas</a></li>
                <li><a href="/admin">Painel admin</a></li>
            </ul>
        </div>
    </body>
    </html>
    """)


@app.get("/live")
def live_page():
    return HTMLResponse("""
    <html>
    <head>
    <title>Live Parking</title>
    <style>
        body { font-family: sans-serif; background: #111; color: #eee; margin:0; padding:20px; }
        h1 { margin-bottom: 0.25rem; }
        .links a { color: #3a8ef6; text-decoration: none; }
        .layout { display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }
        #video-wrapper, #spots-wrapper { background: #1a1a1a; padding: 16px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.4); flex: 1 1 320px; }
        #video-wrapper img { width: 100%; border-radius: 8px; background: #000; border: 1px solid #333; }
        #spots { display: flex; flex-wrap: wrap; gap: 10px; }
        .spot {
            padding: 10px 14px;
            border-radius: 8px;
            min-width: 200px;
            background: #222;
            box-shadow: 0 0 10px rgba(0,0,0,0.4);
        }
        #plate-events { margin-top: 16px; background: #222; padding: 10px; border-radius: 8px; max-height: 240px; overflow-y: auto; }
        #plate-events h3 { margin-top: 0; }
        .event-item { font-size: 0.9rem; border-bottom: 1px solid #333; padding: 6px 0; }
        .event-item:last-child { border-bottom: none; }
    </style>
    </head>
    <body>
        <h1>Monitor de Estacionamento</h1>
        <p class="links"><a href="/reservations">Reservar uma vaga</a> | <a href="/admin">Admin</a> | <a href="/login">Login</a></p>
        <div class="layout">
            <div id="video-wrapper">
                <h2>Video anotado</h2>
                <img id="video-stream" src="/video_feed" alt="Video ao vivo das vagas" />
            </div>
            <div id="spots-wrapper">
                <h2>Estado das Vagas (WebSocket)</h2>
                <div id="spots">A ligar ao servidor...</div>
                <div id="plate-events">
                    <h3>Ultimas matriculas</h3>
                    <div id="plate-events-list">Sem eventos ainda.</div>
                </div>
            </div>
        </div>

        <script>
        const spotsDiv = document.getElementById("spots");
        const eventsDiv = document.getElementById("plate-events-list");
        const ws = new WebSocket("ws://" + location.host + "/ws");

        ws.onopen = () => {
            spotsDiv.innerHTML = "A espera de dados...";
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
                const prob = data[name].prob !== undefined ? Number(data[name].prob).toFixed(2) : "--";
                const plate = data[name].plate;
                const reserved = Boolean(data[name].reserved);
                const violation = Boolean(data[name].violation);
                const reservationInfo = data[name].reservation;
                s.style.background = occ ? "#b00020" : "#006400";
                s.style.border = reserved ? "2px solid #3a8ef6" : "none";
                if (violation) {
                    s.style.background = "#8b0000";
                }
                let text = name + " -> " + (occ ? "OCUPADO" : "LIVRE") + " (" + prob + ")";
                if (reserved) {
                    text += " [RESERVADO]";
                }
                if (plate) {
                    text += " | Placa: " + plate;
                }
                if (violation) {
                    text += " [VIOLACAO]";
                }
                if (reservationInfo && reservationInfo.plate) {
                    text += " @(" + reservationInfo.plate + ")";
                }
                s.innerText = text;
                spotsDiv.appendChild(s);
            }
        };

        ws.onerror = (e) => {
            console.error("WebSocket error", e);
        };

        ws.onclose = () => {
            spotsDiv.innerHTML = "Ligacao WebSocket fechada.";
        };

        async function refreshPlateEvents() {
            try {
                const resp = await fetch("/plate_events");
                if (!resp.ok) {
                    return;
                }
                const events = await resp.json();
                if (!events || events.length === 0) {
                    eventsDiv.textContent = "Sem eventos ainda.";
                    return;
                }
                eventsDiv.innerHTML = "";
                events.forEach(evt => {
                    const div = document.createElement("div");
                    div.className = "event-item";
                    const ts = evt.timestamp ? new Date(evt.timestamp * 1000).toLocaleTimeString() : "";
                    const conf = evt.ocr_conf !== null && evt.ocr_conf !== undefined ? Number(evt.ocr_conf).toFixed(2) : "--";
                    const reserved = evt.reserved ? " [RESERVADO]" : "";
                    const violation = evt.violation ? " VIOLACAO" : "";
                    div.textContent = `[${ts}] ${evt.spot}${reserved}: ${evt.plate} (conf ${conf})${violation}`;
                    eventsDiv.appendChild(div);
                });
            } catch (err) {
                console.error("Erro ao buscar eventos de placa", err);
            }
        }

        refreshPlateEvents();
        setInterval(refreshPlateEvents, 5000);
        </script>
    </body>
    </html>
    """)


@app.get("/reservations")
def reservations_page():
    return HTMLResponse("""
    <html>
    <head>
    <title>Reservas de Vagas</title>
    <style>
        body { font-family: sans-serif; background: #10131a; color: #eee; margin:0; padding:20px; }
        h1 { margin-bottom: 0.25rem; }
        .links a { color: #3a8ef6; text-decoration: none; }
        #auth-info { margin: 10px 0 20px 0; padding: 10px; border-radius: 8px; background: #1a1f2b; }
        #reservation-form-wrapper { display: none; }
        form { display: flex; flex-direction: column; gap: 10px; background: #1a1f2b; padding: 20px; border-radius: 10px; max-width: 420px; }
        input { padding: 8px 10px; border: 1px solid #444; border-radius: 6px; background: #0d1016; color: #eee; }
        button { padding: 10px; border: none; border-radius: 6px; background: #3a8ef6; color: #fff; font-weight: bold; cursor: pointer; }
        button.danger { background: #b00020; }
        #reservation-list { margin-top: 20px; display: flex; flex-direction: column; gap: 8px; }
        .reservation-item { background: #1a1f2b; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #333; }
        .reservation-item span { font-size: 0.9rem; }
        .reservation-item button { padding: 6px 10px; }
        #reservation-spots { margin-top: 15px; display: flex; flex-wrap: wrap; gap: 10px; }
        .spot { padding: 10px 14px; border-radius: 8px; min-width: 200px; background: #222; box-shadow: 0 0 10px rgba(0,0,0,0.4); }
    </style>
    </head>
    <body>
        <h1>Reservar vaga</h1>
        <p class="links"><a href="/live">Voltar ao monitor ao vivo</a> | <a href="/login">Login</a> | <a href="/admin">Admin</a></p>
        <div id="auth-info">A verificar autenticaï¿½ï¿½o...</div>
        <div id="reservation-form-wrapper">
            <form id="reservation-form">
                <label>
                    Vaga
                    <input id="reserve-spot" list="spots-datalist" placeholder="P01" required />
                    <datalist id="spots-datalist"></datalist>
                </label>
                <button type="submit">Reservar por 24h</button>
            </form>
        </div>
        <section>
            <h2>Reservas ativas</h2>
            <div id="reservation-list">Sem reservas.</div>
        </section>
        <section>
            <h2>Estado das vagas</h2>
            <div id="reservation-spots">A ligar ao servidor...</div>
        </section>

        <script>
        const formWrapper = document.getElementById("reservation-form-wrapper");
        const form = document.getElementById("reservation-form");
        const spotInput = document.getElementById("reserve-spot");
        const datalist = document.getElementById("spots-datalist");
        const reservationList = document.getElementById("reservation-list");
        const reservationSpotsDiv = document.getElementById("reservation-spots");
        const authInfo = document.getElementById("auth-info");
        let currentUser = null;

        async function updateAuthInfo() {
            try {
                const resp = await fetch("/api/auth/me");
                if (!resp.ok) throw new Error("not auth");
                currentUser = await resp.json();
                authInfo.innerHTML = `Ligado como <strong>${currentUser.name}</strong> (${currentUser.plate}) <button id="logout-btn">Sair</button>`;
                formWrapper.style.display = "block";
                const logoutBtn = document.getElementById("logout-btn");
                if (logoutBtn) {{
                    logoutBtn.onclick = logout;
                }}
            } catch (err) {
                currentUser = null;
                authInfo.innerHTML = `Precisa fazer <a href="/login">login</a> para reservar.`;
                formWrapper.style.display = "none";
            }
        }

        async function logout() {
            await fetch("/api/auth/logout", { method: "POST" });
            updateAuthInfo();
        }

        async function loadSpots() {
            try {
                const resp = await fetch("/parking");
                if (!resp.ok) {
                    return;
                }
                const data = await resp.json();
                const names = Object.keys(data || {}).sort();
                if (datalist) {
                    datalist.innerHTML = "";
                    names.forEach(name => {
                        const opt = document.createElement("option");
                        opt.value = name;
                        datalist.appendChild(opt);
                    });
                }
            } catch (err) {
                console.error("Erro ao carregar vagas", err);
            }
        }

        async function refreshReservations() {
            if (!reservationList) return;
            try {
                const resp = await fetch("/api/reservations");
                if (!resp.ok) {
                    return;
                }
                const reservations = await resp.json();
                if (!reservations || reservations.length === 0) {
                    reservationList.textContent = "Sem reservas.";
                    return;
                }
                reservationList.innerHTML = "";
                reservations.forEach(res => {
                    const div = document.createElement("div");
                    div.className = "reservation-item";
                    const exp = res.expires_at ? new Date(res.expires_at * 1000).toLocaleString() : "";
                    div.innerHTML = `<span><strong>${res.spot}</strong> reservado atÃ© ${exp}</span><button type="button" class="danger" onclick="cancelReservation('${res.spot}')">Cancelar</button>`;
                    reservationList.appendChild(div);
                });
            } catch (err) {
                console.error("Erro ao buscar reservas", err);
            }
        }

        async function submitReservation(spot) {
            const resp = await fetch("/api/reservations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ spot }),
            });
            if (!resp.ok) {
                const text = await resp.text();
                alert("Erro ao reservar: " + text);
                return;
            }
            refreshReservations();
        }

        if (form && spotInput) {
            form.addEventListener("submit", (ev) => {
                ev.preventDefault();
                submitReservation(spotInput.value);
                spotInput.value = "";
            });
        }

        async function cancelReservation(spot) {
            try {
                const resp = await fetch("/api/reservations/" + encodeURIComponent(spot), { method: "DELETE" });
                if (!resp.ok) {
                    const text = await resp.text();
                    alert("Erro ao cancelar: " + text);
                    return;
                }
                refreshReservations();
            } catch (err) {
                console.error("Erro ao cancelar reserva", err);
            }
        }

        window.cancelReservation = cancelReservation;
        loadSpots();
        refreshReservations();
        updateAuthInfo();
        setInterval(refreshReservations, 10000);
        if (reservationSpotsDiv) {
            const wsRes = new WebSocket("ws://" + location.host + "/ws");
            wsRes.onopen = () => {
                reservationSpotsDiv.textContent = "A espera de dados...";
            };
            wsRes.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const names = Object.keys(data || {}).sort();
                if (names.length === 0) {
                    reservationSpotsDiv.textContent = "Sem dados.";
                    return;
                }
                reservationSpotsDiv.innerHTML = "";
                names.forEach(name => {
                    const info = data[name];
                    const s = document.createElement("div");
                    s.className = "spot";
                    const occ = info.occupied;
                    const reserved = Boolean(info.reserved);
                    const violation = Boolean(info.violation);
                    if (violation) {
                        s.style.background = "#8b0000";
                    } else if (reserved) {
                        s.style.background = occ ? "#0060b0" : "#1a5fb4";
                    } else {
                        s.style.background = occ ? "#b00020" : "#006400";
                    }
                    s.style.border = reserved ? "2px solid #3a8ef6" : "none";
                    let text = name + " -> " + (occ ? "OCUPADO" : "LIVRE");
                    if (reserved) {
                        text += " [RESERVADO]";
                    }
                    if (violation) {
                        text += " [VIOLACAO]";
                    }
                    s.innerText = text;
                    reservationSpotsDiv.appendChild(s);
                });
            };
            wsRes.onerror = () => {
                reservationSpotsDiv.textContent = "Erro no WebSocket.";
            };
            wsRes.onclose = () => {
                reservationSpotsDiv.textContent = "Ligacao WebSocket fechada.";
            };
        }
        </script>
    </body>
    </html>
    """)


@app.get("/login")
def login_page():
    return HTMLResponse("""
    <html>
    <head>
    <title>Login - Parking</title>
    <style>
        body { font-family: sans-serif; background: #0e1117; color: #f1f1f1; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin:0; }
        .card { background: #1a1f2b; padding: 30px; border-radius: 12px; box-shadow: 0 0 25px rgba(0,0,0,0.5); width: 360px; }
        form { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
        input { padding: 8px 10px; border-radius: 6px; border: 1px solid #444; background: #0c0f16; color: #eee; }
        button { padding: 10px; border: none; border-radius: 6px; background: #3a8ef6; color: #fff; font-weight: bold; cursor: pointer; }
        .tabs { display: flex; gap: 10px; margin-bottom: 15px; }
        .tabs button { flex: 1; padding: 8px; border-radius: 6px; border: none; cursor: pointer; }
        .tabs button.active { background: #3a8ef6; color: #fff; }
        #message { margin-top: 10px; min-height: 20px; }
    </style>
    </head>
    <body>
        <div class="card">
            <h2>Entrar / Registar</h2>
            <div class="tabs">
                <button id="tab-login" class="active">Login</button>
                <button id="tab-register">Registar</button>
            </div>
            <form id="auth-form">
                <label>Nome<input id="auth-name" required /></label>
                <label>Placa<input id="auth-plate" required /></label>
                <button type="submit">Continuar</button>
            </form>
            <div id="message"></div>
            <p><a href="/reservations">Ir para reservas</a></p>
        </div>

        <script>
        const form = document.getElementById("auth-form");
        const nameInput = document.getElementById("auth-name");
        const plateInput = document.getElementById("auth-plate");
        const tabLogin = document.getElementById("tab-login");
        const tabRegister = document.getElementById("tab-register");
        const message = document.getElementById("message");
        let mode = "login";

        function setMode(newMode) {
            mode = newMode;
            tabLogin.classList.toggle("active", mode === "login");
            tabRegister.classList.toggle("active", mode === "register");
        }

        tabLogin.addEventListener("click", () => setMode("login"));
        tabRegister.addEventListener("click", () => setMode("register"));

        form.addEventListener("submit", async (ev) => {
            ev.preventDefault();
            message.textContent = "A processar...";
            try {
                const resp = await fetch("/api/auth/" + mode, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        name: nameInput.value,
                        plate: plateInput.value,
                    }),
                });
                if (!resp.ok) {
                    const text = await resp.text();
                    throw new Error(text);
                }
                message.textContent = "Sucesso! Redirecionando...";
                setTimeout(() => window.location.href = "/reservations", 800);
            } catch (err) {
                message.textContent = "Erro: " + err.message;
            }
        });
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # nÃ£o esperamos nada do cliente; sÃ³ mantemos a ligaÃ§Ã£o aberta
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ------------------------------------------------------------
# STARTUP: arrancar thread + apanhar event loop
# ------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    global event_loop, db_pool
    event_loop = asyncio.get_running_loop()
    
    # Criar pool de conexões à base de dados
    if DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            print("[INFO] Pool de conexões PostgreSQL criado com sucesso.")
            await refresh_users_cache()
            await refresh_reservations_cache()
        except Exception as e:
            print(f"[ERRO] Falha ao conectar à base de dados: {e}")
            db_pool = None
    else:
        print("[WARN] DATABASE_URL não configurada.")
    
    t = threading.Thread(target=parking_monitor_loop, daemon=True)
    t.start()
    print("[INFO] Thread de monitorização iniciada.")
@app.get("/admin")
def admin_page(request: Request):
    user = get_session_user(request)
    if not user:
        return HTMLResponse("""
        <html><body style="font-family:sans-serif;background:#10131a;color:#eee;padding:40px;">
        <h1>Admin</h1>
        <p>Precisa fazer <a href="/login">login</a> para aceder ao painel.</p>
        <p><a href="/reservations">Voltar</a></p>
        </body></html>
        """)
    return HTMLResponse(f"""
    <html>
    <head>
    <title>Admin Parking</title>
    <style>
        body {{ font-family: sans-serif; background: #0e1117; color: #f1f1f1; margin:0; padding:20px; }}
        a {{ color: #3a8ef6; text-decoration: none; }}
        .layout {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .panel {{ background: #1a1f2b; padding: 16px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.4); flex: 1 1 320px; }}
        #admin-video img {{ width: 100%; border-radius: 8px; border: 1px solid #333; }}
        .spot {{ padding: 10px 14px; border-radius: 8px; min-width: 200px; background: #222; box-shadow: 0 0 10px rgba(0,0,0,0.4); margin-bottom: 8px; }}
        #admin-spots {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .event-item {{ font-size: 0.9rem; border-bottom: 1px solid #333; padding: 6px 0; }}
        .event-item:last-child {{ border-bottom: none; }}
        #admin-reservations-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .reservation-item {{ background: #222; border-radius: 8px; padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; }}
        .reservation-item button {{ padding: 6px 10px; border: none; border-radius: 6px; background: #b00020; color: #fff; cursor: pointer; }}
    </style>
    </head>
    <body>
        <h1>Painel Admin</h1>
        <p>Ligado como <strong>{user["name"]}</strong> ({user["plate"]}) | <a href="/reservations">Reservas</a> | <a href="/live">Live</a></p>
        <div class="layout">
            <div class="panel" id="admin-video">
                <h2>Video anotado</h2>
                <img src="/video_feed" alt="Live feed" />
            </div>
            <div class="panel">
                <h2>Vagas</h2>
                <div id="admin-spots">A ligar...</div>
            </div>
            <div class="panel">
                <h2>Ultimas matrÃ­culas</h2>
                <div id="admin-events">Sem eventos.</div>
            </div>
            <div class="panel">
                <h2>Reservas ativas</h2>
                <div id="admin-reservations-list">Sem reservas.</div>
            </div>
        </div>

        <script>
        const spotsDiv = document.getElementById("admin-spots");
        const eventsDiv = document.getElementById("admin-events");
        const reservationsDiv = document.getElementById("admin-reservations-list");
        const ws = new WebSocket("ws://" + location.host + "/ws");

        ws.onopen = () => spotsDiv.textContent = "A espera de dados...";
        ws.onmessage = (event) => {{
            const data = JSON.parse(event.data);
            const names = Object.keys(data).sort();
            spotsDiv.innerHTML = "";
            names.forEach(name => {{
                const info = data[name];
                const div = document.createElement("div");
                div.className = "spot";
                let text = name + " -> " + (info.occupied ? "OCUPADO" : "LIVRE") + " (" + (info.prob !== undefined ? Number(info.prob).toFixed(2) : "--") + ")";
                if (info.reserved) text += " [RESERVADO]";
                if (info.plate) text += " | Placa: " + info.plate;
                if (info.violation) text += " [VIOLACAO]";
                if (info.reservation && info.reservation.plate) text += " @(" + info.reservation.plate + ")";
                div.innerText = text;
                spotsDiv.appendChild(div);
            }});
        }};
        ws.onerror = () => spotsDiv.textContent = "Erro no WebSocket.";
        ws.onclose = () => spotsDiv.textContent = "Ligacao WebSocket fechada.";

        async function refreshPlateEvents() {{
            try {{
                const resp = await fetch("/plate_events");
                if (!resp.ok) return;
                const events = await resp.json();
                if (!events || events.length === 0) {{
                    eventsDiv.textContent = "Sem eventos.";
                    return;
                }}
                eventsDiv.innerHTML = "";
                events.forEach(evt => {{
                    const conf = (evt.ocr_conf !== undefined && evt.ocr_conf !== null) ? Number(evt.ocr_conf).toFixed(2) : "--";
                    const div = document.createElement("div");
                    div.className = "event-item";
                    const ts = evt.timestamp ? new Date(evt.timestamp * 1000).toLocaleTimeString() : "";
                    const reserved = evt.reserved ? " [RESERVADO]" : "";
                    const violation = evt.violation ? " VIOLACAO" : "";
                    div.textContent = `[${{ts}}] ${{evt.spot}}${{reserved}}: ${{evt.plate}} (conf ${{conf}})${{violation}}`;
                    eventsDiv.appendChild(div);
                }});
            }} catch (err) {{
                eventsDiv.textContent = "Erro ao carregar eventos.";
            }}
        }}

        async function refreshReservations() {{
            try {{
                const resp = await fetch("/api/reservations");
                if (!resp.ok) return;
                const reservations = await resp.json();
                if (!reservations || reservations.length === 0) {{
                    reservationsDiv.textContent = "Sem reservas.";
                    return;
                }}
                reservationsDiv.innerHTML = "";
                reservations.forEach(res => {{
                    const div = document.createElement("div");
                    div.className = "reservation-item";
                    const exp = res.expires_at ? new Date(res.expires_at * 1000).toLocaleString() : "";
                    const plateInfo = res.plate ? res.plate : "N/D";
                    div.innerHTML = `<span><strong>${{res.spot}}</strong> -> Placa: ${{plateInfo}}<br/><small>expira ${{exp}}</small></span><button type="button" onclick="cancelReservation('${{res.spot}}')">Cancelar</button>`;
                    reservationsDiv.appendChild(div);
                }});
            }} catch (err) {{
                reservationsDiv.textContent = "Erro ao carregar reservas.";
            }}
        }}

        async function cancelReservation(spot) {{
            try {{
                const resp = await fetch("/api/reservations/" + encodeURIComponent(spot), {{ method: "DELETE" }});
                if (!resp.ok) {{
                    const text = await resp.text();
                    alert("Erro ao cancelar: " + text);
                    return;
                }}
                refreshReservations();
            }} catch (err) {{
                alert("Erro ao cancelar reserva");
            }}
        }}

        window.cancelReservation = cancelReservation;
        refreshPlateEvents();
        refreshReservations();
        setInterval(refreshPlateEvents, 5000);
        setInterval(refreshReservations, 10000);
        </script>
    </body>
    </html>
    """)
