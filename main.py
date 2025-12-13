# main.py â€” FastAPI + Monitor de Estacionamento (CNN only + WebSocket)

from __future__ import annotations

from typing import Any, List, Dict, Optional, Tuple, Sequence
import os
import cv2
import numpy as np
import json
import math
import traceback
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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, UploadFile, File, Form, Header
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
import jwt
import hashlib

from spot_classifier import SpotClassifier
from esp32_capture_wrapper import get_video_capture

try:
    from supabaseStorage import SupabaseStorageService
except ImportError:
    SupabaseStorageService = None

# Novo módulo de autenticação v2.0
try:
    from auth_routes import router as auth_router, set_db_pool as set_auth_db_pool
except ImportError:
    auth_router = None
    set_auth_db_pool = None


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

# CORS for React Native mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for mobile app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registar router de autenticação v2.0
if auth_router:
    app.include_router(auth_router)
    print("[INFO] Router de autenticação v2.0 registado.")

# JWT Configuration for mobile authentication
JWT_SECRET = os.getenv("JWT_SECRET", SESSION_SECRET)  # Use same secret if not specified
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

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
    """Refresh cache of users with their vehicles (for plate lookup)."""
    if not db_pool:
        with g_users_lock:
            return [
                {"name": info["name"], "plate": info["plate"], "plate_norm": info["plate_norm"]}
                for info in g_users.values()
            ]
    async with db_pool.acquire() as conn:
        # Query users with their vehicles (new schema)
        rows = await conn.fetch(
            """
            SELECT u.full_name, v.plate, v.plate_norm 
            FROM public.parking_users u
            JOIN public.parking_user_vehicles v ON v.user_id = u.id
            """
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
    """Atualiza cache de reservas ativas (para hoje)."""
    from datetime import date
    if not db_pool:
        with g_reservations_lock:
            return [
                {
                    "spot": spot,
                    "plate": info.get("plate_raw"),
                    "reservation_date": info.get("reservation_date"),
                    "user_id": info.get("user_id"),
                }
                for spot, info in g_active_reservations.items()
            ]
    async with db_pool.acquire() as conn:
        # Buscar reservas ativas (só para hoje)
        rows = await conn.fetch(
            """
            SELECT id, spot, plate, plate_norm, user_id, reservation_date, was_used, created_at 
            FROM public.parking_manual_reservations
            WHERE reservation_date = $1
            """,
            date.today()
        )
    result: List[Dict[str, Any]] = []
    with g_reservations_lock:
        g_active_reservations.clear()
        for row in rows:
            entry = {
                "spot": row["spot"],
                "plate": row["plate"],
                "plate_norm": row["plate_norm"],
                "user_id": row["user_id"],
                "reservation_date": row["reservation_date"].isoformat() if row["reservation_date"] else None,
                "was_used": row["was_used"],
                "created_at": row["created_at"].timestamp() if row["created_at"] else None,
            }
            g_active_reservations[row["spot"]] = {
                "plate_raw": row["plate"],
                "plate_norm": row["plate_norm"],
                "user_id": row["user_id"],
                "reservation_date": entry["reservation_date"],
                "was_used": row["was_used"],
                "created_at": entry["created_at"],
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
    """
    Remove reservas expiradas e aplica multa se não foram usadas.
    Multa = sessão com status 'fine_pending' para reservas não utilizadas.
    """
    now = time.time()
    expired: List[str] = []
    expired_with_fine: List[Dict] = []  # Reservas expiradas que precisam de multa
    
    with g_reservations_lock:
        for spot, info in list(g_active_reservations.items()):
            if info.get("expires_at", 0) <= now:
                expired.append(spot)
                # Guardar info para aplicar multa
                expired_with_fine.append({
                    "spot": spot,
                    "plate": info.get("plate_raw"),
                    "plate_norm": info.get("plate_norm"),
                    "reserved_by": info.get("reserved_by"),
                })
                g_active_reservations.pop(spot, None)
    
    if expired and db_pool and event_loop:
        asyncio.run_coroutine_threadsafe(db_delete_reservations(expired), event_loop)
        # Aplicar multas para reservas não usadas
        asyncio.run_coroutine_threadsafe(
            apply_reservation_fines(expired_with_fine),
            event_loop
        )


async def apply_reservation_fines(expired_reservations: List[Dict]):
    """
    Aplica multa para reservas que expiraram sem serem usadas.
    Cria uma sessão com status 'fine_pending' e amount_due = multa.
    """
    if not db_pool or not expired_reservations:
        return
    
    RESERVATION_FINE = 5.00  # Multa de 5€ por não usar reserva
    
    async with db_pool.acquire() as conn:
        for res in expired_reservations:
            try:
                # Verificar se houve sessão aberta para esta matrícula durante a reserva
                # Se não houve, então não usou a reserva → multa
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM public.parking_sessions
                    WHERE plate_norm = $1 
                      AND spot = $2
                      AND status IN ('open', 'closed')
                    LIMIT 1
                    """,
                    res.get("plate_norm"),
                    res.get("spot"),
                )
                
                if not existing:
                    # Não usou a reserva → criar sessão de multa
                    await conn.execute(
                        """
                        INSERT INTO public.parking_sessions 
                            (plate, plate_norm, spot, status, amount_due, notes)
                        VALUES ($1, $2, $3, 'fine_pending', $4, $5)
                        """,
                        res.get("plate"),
                        res.get("plate_norm"),
                        res.get("spot"),
                        RESERVATION_FINE,
                        f"Multa: reserva do spot {res.get('spot')} expirou sem ser usada",
                    )
                    print(f"[INFO] 💰 Multa aplicada: {res.get('plate')} não usou reserva do {res.get('spot')}")
            except Exception as e:
                print(f"[ERROR] Falha ao aplicar multa: {e}")


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
    
    if plate:
        print(f"[INFO] ✅ ALPR detetou matrícula em {name}: {plate} (conf: {ocr_conf:.2f})" if ocr_conf else f"[INFO] ✅ ALPR detetou matrícula em {name}: {plate}")

    event = {
        "spot": name,
        "plate": plate,
        "ocr_conf": ocr_conf,
        "det_conf": det_conf,
        "timestamp": time.time(),
    }
    return name, event

async def update_session_spot(plate: str, spot: str):
    """
    Atualiza a sessão aberta com a vaga onde o carro estacionou.
    Chamado quando o sistema de CV deteta que uma vaga foi ocupada.
    """
    if not db_pool:
        print("[WARN] update_session_spot: db_pool não disponível")
        return
    
    plate_norm = normalize_plate_text(plate)
    
    async with db_pool.acquire() as conn:
        try:
            # Atualizar APENAS sessões abertas SEM vaga ainda atribuída
            result = await conn.execute(
                """
                UPDATE public.parking_sessions
                SET spot = $1, plate_norm = $2
                WHERE plate = $3 
                  AND status = 'open' 
                  AND spot IS NULL
                  AND exit_time IS NULL
                RETURNING id
                """,
                spot,
                plate_norm,
                plate
            )
            
            # Verificar se atualizou alguma linha
            rows_updated = result.split()[-1]
            if rows_updated != "0":
                print(f"[INFO] ✅ Sessão atualizada: {plate} → vaga {spot}")
            else:
                print(f"[WARN] Nenhuma sessão aberta encontrada para {plate} (pode já ter vaga atribuída)")
                
        except Exception as e:
            print(f"[ERROR] update_session_spot falhou: {e}")

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

    if event.get("plate") and db_pool and event_loop:
        asyncio.run_coroutine_threadsafe(
            update_session_spot(event["plate"], name),
            event_loop
        )

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
    cap = get_video_capture(VIDEO_SOURCE)  # Usa o wrapper inteligente
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
                    
                    # Check for debug override
                    if name in g_debug_spot_overrides:
                        occ_final = g_debug_spot_overrides[name]

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
                        # Ativar ALPR para todas as vagas quando ficam ocupadas
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


@app.get("/api/config")
async def get_config():
    """Return parking configuration for mobile app."""
    return {
        "parking_rate_per_hour": PARKING_RATE_PER_HOUR,
        "currency": "EUR",
    }


# Debug endpoint to manually override spot status for testing
g_debug_spot_overrides: Dict[str, bool] = {}  # spot_name -> occupied (True/False)

class DebugSpotPayload(BaseModel):
    spot: str = Field(..., min_length=1)
    occupied: bool

@app.post("/api/debug/spot")
async def debug_set_spot(payload: DebugSpotPayload):
    """Debug endpoint to force a spot to be occupied or free for testing."""
    g_debug_spot_overrides[payload.spot] = payload.occupied
    status = "ocupado" if payload.occupied else "livre"
    return {"message": f"Spot {payload.spot} definido como {status}", "spot": payload.spot, "occupied": payload.occupied}

@app.delete("/api/debug/spot/{spot_name}")
async def debug_reset_spot(spot_name: str):
    """Reset a spot to use CNN detection instead of manual override."""
    if spot_name in g_debug_spot_overrides:
        del g_debug_spot_overrides[spot_name]
    return {"message": f"Spot {spot_name} resetado para deteção automática"}

@app.get("/api/debug/spots")
async def debug_list_overrides():
    """List all manual spot overrides."""
    return {"overrides": g_debug_spot_overrides}


class ReservationPayload(BaseModel):
    spot: str = Field(..., min_length=1)
    duration_hours: Optional[int] = Field(default=12, ge=1, le=24)  # Default 12h, max 24h


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
    """Endpoint antigo de reservas - mantido para compatibilidade."""
    from datetime import date
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

    plate_norm = normalize_plate_text(plate_value)
    reservation_date = date.today()  # Reserva para hoje

    with g_reservations_lock:
        if spot_name in g_active_reservations:
            raise HTTPException(status_code=409, detail="Esta vaga ja possui uma reserva ativa.")

    if db_pool:
        async with db_pool.acquire() as conn:
            # Obter user_id a partir do plate_norm
            user_row = await conn.fetchrow(
                "SELECT user_id FROM public.parking_user_vehicles WHERE plate_norm = $1",
                plate_norm
            )
            user_id = user_row["user_id"] if user_row else None
            
            try:
                await conn.execute(
                    """
                    INSERT INTO public.parking_manual_reservations
                        (user_id, spot, plate, plate_norm, reservation_date)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user_id,
                    spot_name,
                    plate_value,
                    plate_norm,
                    reservation_date,
                )
            except pg_exceptions.UniqueViolationError:
                raise HTTPException(status_code=409, detail="Esta vaga ja possui uma reserva ativa.")
        await refresh_reservations_cache()
    else:
        with g_reservations_lock:
            g_active_reservations[spot_name] = {
                "plate_raw": plate_value,
                "plate_norm": plate_norm,
                "user_id": None,
                "reservation_date": reservation_date.isoformat(),
                "was_used": False,
                "created_at": time.time(),
            }

    return JSONResponse({"spot": spot_name, "plate": plate_value, "reservation_date": reservation_date.isoformat()})


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


# NOTE: /api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/me
# are now handled by auth_routes.py (included via auth_router above)
# The auth_routes.py uses email/password authentication with JWT tokens


# ------------------------------------------------------------
# JWT HELPER FUNCTIONS (Mobile Authentication)
# ------------------------------------------------------------
def generate_jwt_token(user_data: Dict[str, Any]) -> str:
    """Generate JWT token for mobile app authentication."""
    payload = {
        "name": user_data["name"],
        "plate": user_data["plate"],
        "plate_norm": user_data["plate_norm"],
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return user data."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "name": payload.get("name"),
            "plate": payload.get("plate"),
            "plate_norm": payload.get("plate_norm"),
        }
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_jwt_user(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    """Extract user from Authorization header (Bearer token)."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return verify_jwt_token(parts[1])


# ------------------------------------------------------------
# MOBILE AUTH ENDPOINTS (JWT-based)
# ------------------------------------------------------------
class MobileAuthPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    plate: str = Field(..., min_length=1, max_length=32)


@app.post("/api/mobile/register")
async def mobile_register(payload: MobileAuthPayload):
    """Register new user and return JWT token for mobile app.
    
    Creates a user in parking_users (with a placeholder email based on plate)
    and adds the vehicle in parking_user_vehicles.
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponivel.")
    name = payload.name.strip()
    plate = payload.plate.strip()
    plate_norm = normalize_plate_text(plate)
    if not name or not plate_norm:
        raise HTTPException(status_code=400, detail="Nome e placa validos sao obrigatorios.")
    
    # Generate a placeholder email based on plate (for mobile-only users)
    placeholder_email = f"{plate_norm.lower()}@mobile.tugapark.pt"
    # Generate a hashed placeholder password (user would need to reset if using web)
    import bcrypt
    placeholder_password = bcrypt.hashpw(plate_norm.encode(), bcrypt.gensalt()).decode()
    
    try:
        async with db_pool.acquire() as conn:
            # Check if plate already registered
            existing = await conn.fetchrow(
                "SELECT id FROM public.parking_user_vehicles WHERE plate_norm = $1",
                plate_norm
            )
            if existing:
                raise HTTPException(status_code=400, detail="Placa ja registada.")
            
            # Create user
            user_row = await conn.fetchrow(
                """
                INSERT INTO public.parking_users (email, password_hash, full_name, role)
                VALUES ($1, $2, $3, 'client')
                RETURNING id, full_name
                """,
                placeholder_email,
                placeholder_password,
                name
            )
            
            # Add vehicle
            await conn.execute(
                """
                INSERT INTO public.parking_user_vehicles (user_id, plate, plate_norm, is_primary)
                VALUES ($1, $2, $3, TRUE)
                """,
                user_row["id"],
                plate,
                plate_norm
            )
    except pg_exceptions.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Utilizador ou placa ja registada.")
    
    await refresh_users_cache()
    user_data = {"name": user_row["full_name"], "plate": plate, "plate_norm": plate_norm}
    token = generate_jwt_token(user_data)
    return {"token": token, "user": {"name": user_data["name"], "plate": user_data["plate"]}}


@app.post("/api/mobile/login")
async def mobile_login(payload: MobileAuthPayload):
    """Login user and return JWT token for mobile app."""
    plate_norm = normalize_plate_text(payload.plate)
    if not plate_norm:
        raise HTTPException(status_code=400, detail="Placa invalida.")
    user = await ensure_user_loaded(plate_norm)
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador nao encontrado.")
    if user["name"].strip().lower() != payload.name.strip().lower():
        raise HTTPException(status_code=401, detail="Nome nao confere com a placa.")
    user_data = {"name": user["name"], "plate": user["plate"], "plate_norm": user["plate_norm"]}
    token = generate_jwt_token(user_data)
    return {"token": token, "user": {"name": user_data["name"], "plate": user_data["plate"]}}


@app.get("/api/mobile/me")
async def mobile_me(authorization: Optional[str] = Header(None)):
    """Get current user from JWT token."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    return user


@app.get("/api/mobile/sessions")
async def mobile_sessions(authorization: Optional[str] = Header(None)):
    """Get parking sessions for authenticated mobile user."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    
    if not db_pool:
        return {"sessions": []}
    
    # Use plate for matching since plate_norm may not exist in sessions table
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, plate, entry_time, exit_time, spot, 
                   amount_due, amount_paid, status, payment_deadline, notes
            FROM public.parking_sessions
            WHERE UPPER(REPLACE(REPLACE(plate, '-', ''), ' ', '')) = $1
            ORDER BY entry_time DESC
            LIMIT 20
            """,
            user["plate_norm"],
        )
    
    sessions = []
    for row in rows:
        sessions.append({
            "id": row["id"],
            "plate": row["plate"],
            "entry_time": row["entry_time"].isoformat() if row["entry_time"] else None,
            "exit_time": row["exit_time"].isoformat() if row["exit_time"] else None,
            "spot": row["spot"],
            "amount_due": float(row["amount_due"]) if row["amount_due"] else 0,
            "amount_paid": float(row["amount_paid"]) if row["amount_paid"] else 0,
            "status": row["status"],
            "payment_deadline": row["payment_deadline"].isoformat() if row["payment_deadline"] else None,
            "notes": row["notes"],
        })
    
    return {"sessions": sessions}


@app.get("/api/mobile/reservations")
async def mobile_reservations(authorization: Optional[str] = Header(None)):
    """Get reservations for authenticated mobile user."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    
    records = await refresh_reservations_cache()
    user_reservations = [
        r for r in records 
        if r.get("plate_norm") == user["plate_norm"]
    ]
    return {"reservations": user_reservations}


@app.post("/api/mobile/reservations")
async def mobile_create_reservation(
    payload: ReservationPayload, 
    authorization: Optional[str] = Header(None)
):
    """Create reservation for authenticated mobile user."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    
    ensure_spot_meta_loaded()
    spot_name = resolve_spot_name(payload.spot)
    if spot_name is None:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")
    
    meta = g_spot_meta.get(spot_name, {})
    if meta.get("reserved"):
        raise HTTPException(status_code=400, detail="Esta vaga ja esta reservada permanentemente.")

    with g_lock:
        spot_state = g_spot_status.get(spot_name)
    if spot_state and spot_state.get("occupied"):
        raise HTTPException(status_code=400, detail="Nao e possivel reservar uma vaga ocupada.")

    prune_expired_reservations()

    RESERVATION_EXPIRY_HOURS = payload.duration_hours or 12
    expires_at = time.time() + RESERVATION_EXPIRY_HOURS * 3600

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
                    user["plate"],
                    user["plate_norm"],
                    user["name"],
                    expires_dt,
                )
            except pg_exceptions.UniqueViolationError:
                raise HTTPException(status_code=409, detail="Esta vaga ja possui uma reserva ativa.")
        await refresh_reservations_cache()
    
    return {"spot": spot_name, "plate": user["plate"], "expires_at": expires_at, "duration_hours": RESERVATION_EXPIRY_HOURS}


@app.delete("/api/mobile/reservations/{spot_name}")
async def mobile_cancel_reservation(spot_name: str, authorization: Optional[str] = Header(None)):
    """Cancel a reservation for authenticated mobile user."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    
    resolved_spot = resolve_spot_name(spot_name)
    if not resolved_spot:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada.")
    
    # Check if user owns this reservation
    with g_reservations_lock:
        reservation = g_active_reservations.get(resolved_spot)
        if not reservation:
            raise HTTPException(status_code=404, detail="Reserva nao encontrada.")
        if reservation.get("plate_norm") != user["plate_norm"]:
            raise HTTPException(status_code=403, detail="Esta reserva nao pertence a si.")
        
        # Remove from memory
        del g_active_reservations[resolved_spot]
    
    # Remove from database
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM public.parking_manual_reservations 
                WHERE spot = $1 AND plate_norm = $2
                """,
                resolved_spot,
                user["plate_norm"],
            )
        await refresh_reservations_cache()
    
    return {"message": f"Reserva da vaga {resolved_spot} cancelada com sucesso."}

@app.post("/api/mobile/payments")
async def mobile_payments(payload: PaymentPayload, authorization: Optional[str] = Header(None)):
    """Process payment for authenticated mobile user."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    
    session_id = payload.session_id
    amount = round(payload.amount, 2)
    method = payload.method
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")
    
    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT id, plate, amount_due, amount_paid, status
            FROM public.parking_sessions
            WHERE id = $1
            """,
            session_id,
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
        
        # Verify session belongs to user (compare normalized plates)
        session_plate_norm = normalize_plate_text(session["plate"])
        if session_plate_norm != user["plate_norm"]:
            raise HTTPException(status_code=403, detail="Sessao nao pertence a este utilizador.")
        
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
        payment_deadline = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
        
        await conn.execute(
            """
            UPDATE public.parking_sessions
            SET amount_paid = $1, status = $2, payment_deadline = $3
            WHERE id = $4
            """,
            new_paid,
            new_status,
            payment_deadline,
            session_id,
        )
        
        print(f"[PAYMENT] ✅ Mobile payment: Session {session_id} | Amount: €{amount} | Deadline: {payment_deadline.isoformat()}")
    
    return {
        "session_id": session_id,
        "amount_paid": float(new_paid),
        "amount_due": float(amount_due),
        "status": new_status,
        "payment_method": method,
        "payment_amount": float(amount),
        "payment_deadline": payment_deadline.isoformat(),
        "message": "Pagamento efetuado! Tem 15 minutos para sair do parque."
    }


# ------------------------------------------------------------
# Função auxiliar para processar imagem e detectar matrícula
# ------------------------------------------------------------
async def process_plate_image(image_bytes: bytes) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Processa uma imagem e extrai a matrícula usando fast-alpr.
    Retorna uma tupla: (matrícula detectada, imagem anotada em bytes)
    ou (None, None) se não detectar nada.
    """
    try:
        # Converter bytes para numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None, None
        
        # Obter instância ALPR
        alpr = get_alpr_instance()
        if alpr is None:
            return None, None
        
        # Executar detecção
        results = alpr.predict(img)
        
        if not results:
            return None, None
        
        # Pegar o primeiro resultado
        first = results[0] if isinstance(results, (list, tuple)) else results
        plate_text = getattr(first.ocr, "text", None) if getattr(first, "ocr", None) else None
        
        # Desenhar as predições na imagem
        annotated_img = alpr.draw_predictions(img)
        
        # Converter imagem anotada de volta para bytes (JPEG)
        success, buffer = cv2.imencode('.jpg', annotated_img)
        if success:
            annotated_bytes = buffer.tobytes()
        else:
            annotated_bytes = None
        
        return plate_text, annotated_bytes
        
    except Exception as e:
        print(f"[ERRO] Falha ao processar imagem ALPR: {e}")
        return None, None


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
    
    # Processar com ALPR e obter imagem anotada
    plate, annotated_image_bytes = await process_plate_image(image_bytes)
    
    if not plate:
        raise HTTPException(status_code=400, detail="Nenhuma matricula detectada na imagem.")
    
    # Usar imagem anotada para upload, ou original se anotação falhou
    upload_bytes = annotated_image_bytes if annotated_image_bytes else image_bytes
    
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
                # Já existe sessão aberta - retornar HTTP 409 (Conflict)
                raise HTTPException(
                    status_code=409,
                    detail=f"Veículo {plate} já tem uma sessão aberta (ID: {existing_session['id']}). Acesso negado."
                )
            
            # Não existe sessão aberta - fazer upload da imagem AGORA
            image_url = None
            if supabase_storage:
                try:
                    image_url = supabase_storage.upload_and_get_url(
                        image_bytes=upload_bytes,
                        plate=plate,
                        expires_in=365 * 24 * 3600,  # 1 ano
                        ext="jpg"
                    )
                    print(f"[INFO] Imagem uploaded: {image_url}")
                except Exception as e:
                    print(f"[WARN] Falha ao fazer upload da imagem: {e}")
                    # Não bloqueia o fluxo caso falhe o upload
            
            # Criar nova entrada com a URL da imagem
            plate_norm = normalize_plate_text(plate)
            
            # Procurar user_id pelo veículo registado
            user_id = None
            vehicle_row = await conn.fetchrow(
                """
                SELECT user_id FROM public.parking_user_vehicles 
                WHERE plate_norm = $1
                LIMIT 1
                """,
                plate_norm
            )
            if vehicle_row:
                user_id = vehicle_row["user_id"]
                print(f"[INFO] Veículo {plate} associado ao user_id: {user_id}")
            
            row = await conn.fetchrow(
                """
                INSERT INTO public.parking_sessions (user_id, plate, plate_norm, camera_id, status, entry_image_url)
                VALUES ($1, $2, $3, $4, 'open', $5)
                RETURNING id, entry_time
                """,
                user_id,
                plate,
                plate_norm,
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
    VALIDA: Pagamento efetuado + Deadline de 10min não expirado
    Recebe imagem da matrícula do ESP32 e usa ALPR para detectar a placa.
    """
    if not camera_id:
        raise HTTPException(status_code=400, detail="camera_id obrigatório.")
    
    # Ler imagem
    image_bytes = await image.read()
    
    # Processar com ALPR e obter imagem anotada
    plate, annotated_image_bytes = await process_plate_image(image_bytes)
    
    if not plate:
        raise HTTPException(status_code=400, detail="Nenhuma matricula detectada na imagem.")
    
    # Normalizar matrícula para comparação
    plate_norm = normalize_plate_text(plate)
    
    # Usar imagem anotada para upload, ou original se anotação falhou
    upload_bytes = annotated_image_bytes if annotated_image_bytes else image_bytes
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")
    
    async with db_pool.acquire() as conn:
        # Buscar sessão aberta OU paga (usar plate_norm para comparação)
        # Status 'open' = ainda não pagou, 'paid' = pagou e pode sair
        session = await conn.fetchrow(
            """
            SELECT id, plate, entry_time, exit_time, spot, amount_due, amount_paid, payment_deadline, status
            FROM public.parking_sessions
            WHERE (plate_norm = $1 OR plate = $2)
              AND status IN ('open', 'paid')
              AND exit_time IS NULL
            ORDER BY entry_time DESC
            LIMIT 1
            """,
            plate_norm,
            plate,
        )
        
        # DEBUG: Ver o que está a ser procurado
        print(f"[EXIT DEBUG] Placa detectada: {plate}")
        print(f"[EXIT DEBUG] Placa normalizada: {plate_norm}")
        print(f"[EXIT DEBUG] Sessão encontrada: {session}")
        
        if not session:
            # DEBUG: Procurar qualquer sessão com esta placa para ver o status
            debug_session = await conn.fetchrow(
                """
                SELECT id, plate, plate_norm, status, exit_time, amount_paid
                FROM public.parking_sessions
                WHERE (plate_norm = $1 OR plate = $2)
                ORDER BY entry_time DESC
                LIMIT 1
                """,
                plate_norm,
                plate,
            )
            print(f"[EXIT DEBUG] Sessão mais recente (qualquer status): {debug_session}")
            
            raise HTTPException(
                status_code=404, 
                detail="Nenhuma sessao aberta encontrada para esta placa."
            )
        
        # CALCULAR VALOR A PAGAR
        entry_time = session["entry_time"]
        now = datetime.now(tz=timezone.utc)
        duration_seconds = (now - entry_time).total_seconds()
        duration_hours = duration_seconds / 3600
        
        # Buscar taxa de estacionamento
        parking_rate = float(os.getenv("PARKING_RATE_PER_HOUR", "1.50"))
        billing_step = int(os.getenv("PARKING_BILLING_MINUTE_STEP", "1"))
        
        # Calcular valor (arredondar para cima por minuto)
        duration_minutes = math.ceil(duration_seconds / 60)
        billable_minutes = math.ceil(duration_minutes / billing_step) * billing_step
        amount_due = (billable_minutes / 60) * parking_rate
        min_fee = float(os.getenv("PARKING_MINIMUM_FEE", "0"))
        amount_due = max(amount_due, min_fee)
        
        # Atualizar amount_due na sessão
        await conn.execute(
            "UPDATE public.parking_sessions SET amount_due = $1 WHERE id = $2",
            amount_due,
            session["id"]
        )
        
        print(f"[EXIT] Duração: {duration_minutes} min | Taxa: €{parking_rate}/h | Valor: €{amount_due:.2f}")
        
        # VERIFICAR SE JÁ ESTÁ PAGO
        amount_paid = float(session["amount_paid"]) if session["amount_paid"] else 0
        
        if amount_paid >= amount_due:
            # Já está pago - verificar deadline
            if session["payment_deadline"]:
                if now > session["payment_deadline"]:
                    raise HTTPException(
                        status_code=403,
                        detail="Pagamento expirado (prazo de 10min excedido). Efetue novo pagamento."
                    )
            # Pode sair!
            print(f"[EXIT] ✅ Já pago (€{amount_paid:.2f}) - permitir saída")
        else:
            # NÃO ESTÁ PAGO - TENTAR PAGAMENTO AUTOMÁTICO
            # Buscar user_id pelo veículo
            plate_user = await conn.fetchrow(
                "SELECT user_id FROM public.parking_user_vehicles WHERE plate_norm = $1 LIMIT 1",
                plate_norm
            )
            user_id = plate_user["user_id"] if plate_user else None
            
            auto_payment_done = False
            
            if user_id:
                # Verificar se tem cartão com auto_pay ativado
                auto_pay_card = await conn.fetchrow(
                    """
                    SELECT id, card_type, card_last_four, card_holder_name
                    FROM public.parking_user_payment_methods
                    WHERE user_id = $1 AND auto_pay = TRUE
                    LIMIT 1
                    """,
                    user_id
                )
                
                if auto_pay_card:
                    # FAZER PAGAMENTO AUTOMÁTICO
                    print(f"[EXIT] 💳 Auto-pay ativado - Cobrando €{amount_due:.2f} do cartão {auto_pay_card['card_type']} ****{auto_pay_card['card_last_four']}")
                    
                    # Simular pagamento (em produção seria integração com gateway)
                    payment_deadline = now + timedelta(minutes=10)
                    
                    await conn.execute(
                        """
                        UPDATE public.parking_sessions 
                        SET amount_paid = $1, status = 'paid', payment_deadline = $2
                        WHERE id = $3
                        """,
                        amount_due,
                        payment_deadline,
                        session["id"]
                    )
                    
                    # Criar registo de pagamento
                    await conn.execute(
                        """
                        INSERT INTO public.parking_payments (session_id, amount, payment_method, payment_type)
                        VALUES ($1, $2, $3, 'auto_exit')
                        """,
                        session["id"],
                        amount_due,
                        f"card_{auto_pay_card['card_last_four']}"
                    )
                    
                    print(f"[EXIT] ✅ Pagamento automático efetuado! Valor: €{amount_due:.2f}")
                    auto_payment_done = True
            
            if not auto_payment_done:
                # Não tem auto-pay - exigir pagamento manual
                raise HTTPException(
                    status_code=402,
                    detail=f"Pagamento nao efetuado. Valor a pagar: €{amount_due:.2f}. Use o app para pagar antes de sair."
                )
        
        session_id = session["id"]
        entry_time = session["entry_time"]
        exit_time = datetime.now(tz=timezone.utc)
        
        # Upload da imagem de saída para Supabase
        exit_image_url = None
        if supabase_storage:
            try:
                exit_image_url = supabase_storage.upload_and_get_url(
                    image_bytes=upload_bytes,
                    plate=f"{plate}/exit",
                    expires_in=365 * 24 * 3600,
                    ext="jpg"
                )
                print(f"[INFO] Imagem de saída uploaded: {exit_image_url}")
            except Exception as e:
                print(f"[WARN] Falha ao fazer upload da imagem de saída: {e}")
        
        # ✅ ATUALIZAR SESSÃO - Fechar com status 'closed'
        await conn.execute(
            """
            UPDATE public.parking_sessions
            SET exit_time = $1, status = 'closed', exit_image_url = $2
            WHERE id = $3
            """,
            exit_time,
            exit_image_url,
            session_id,
        )
        
        print(f"[EXIT] ✅ Saída autorizada: {plate} (vaga {session['spot']})")
    
    return JSONResponse({
        "session_id": session_id,
        "plate": session["plate"],
        "entry_time": entry_time.isoformat(),
        "exit_time": exit_time.isoformat(),
        "amount_due": float(session["amount_due"] or 0),
        "amount_paid": float(session["amount_paid"] or 0),
        "spot": session["spot"],
        "camera_id": camera_id,
        "message": "Saida autorizada. Boa viagem!"
    })


@app.post("/api/parking-spot-occupied")
async def parking_spot_occupied(
    request: Request,
    spot_id: str = Form(...),
    camera_id: str = Form(...)
):
    """
    Endpoint chamado pela ESP32-CAM quando uma vaga fica ocupada.
    Recebe: foto + spot_id (ex: 'A1')
    Processa: ALPR para obter matrícula
    Atualiza: sessão aberta com a vaga
    """
    try:
        # 1. Receber imagem
        form_data = await request.form()
        image_file = form_data.get("imageFile")
        
        if not image_file:
            return JSONResponse(
                status_code=400,
                content={"error": "No image provided"}
            )
        
        # 2. Ler bytes da imagem
        image_bytes = await image_file.read()
        
        print(f"[INFO] Vaga {spot_id} ocupada, processando ALPR...")
        
        # 3. Executar ALPR
        plate = await run_alpr_on_image(image_bytes)
        
        if not plate:
            print(f"[WARN] Nenhuma matrícula detetada na vaga {spot_id}")
            return JSONResponse(
                status_code=200,
                content={"success": False, "message": "No plate detected"}
            )
        
        # 4. Atualizar sessão com a vaga
        plate_norm = normalize_plate_text(plate)
        
        if db_pool:
            async with db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE public.parking_sessions
                    SET spot = $1
                    WHERE plate_norm = $2 
                      AND status = 'open' 
                      AND spot IS NULL
                    RETURNING id
                    """,
                    spot_id,
                    plate_norm
                )
                
                if result.split()[-1] == "0":
                    print(f"[WARN] Nenhuma sessão aberta encontrada para {plate}")
                    return JSONResponse(
                        status_code=404,
                        content={"error": "No open session found for this plate"}
                    )
                
                print(f"[SUCCESS] Sessão atualizada: {plate} → Vaga {spot_id}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "plate": plate,
                "spot": spot_id
            }
        )
        
    except Exception as e:
        print(f"[ERROR] /api/parking-spot-occupied: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

async def run_alpr_on_image(image_bytes: bytes) -> Optional[str]:
    """
    Executa ALPR numa imagem e retorna a matrícula detetada.
    """
    try:
        # Converter bytes para imagem OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("[ERROR] Falha ao descodificar imagem")
            return None
        
        # Executar ALPR (usar a mesma lógica do alpr.py)
        from alpr import recognize_plate_easyocr
        
        plate_text = recognize_plate_easyocr(img)
        
        if plate_text and len(plate_text) >= 6:
            return plate_text.upper().replace(" ", "")
        
        return None
        
    except Exception as e:
        print(f"[ERROR] run_alpr_on_image: {e}")
        return None

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
        
        # ✅ Inserir registo de pagamento
        await conn.execute(
            """
            INSERT INTO public.parking_payments (session_id, amount, method, payment_type)
            VALUES ($1, $2, $3, 'parking')
            """,
            session_id,
            amount,
            method,
        )
        
        current_paid = session["amount_paid"] or 0
        new_paid = round(current_paid + amount, 2)
        amount_due = session["amount_due"] or 0
        
        new_status = 'paid' if new_paid >= amount_due else session["status"]
        
        # ✅ DEFINIR DEADLINE DE 10 MINUTOS PARA SAÍDA
        from datetime import timedelta
        payment_deadline = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
        
        # ✅ Atualizar sessão com pagamento E deadline
        await conn.execute(
            """
            UPDATE public.parking_sessions
            SET amount_paid = $1, status = $2, payment_deadline = $3
            WHERE id = $4
            """,
            new_paid,
            new_status,
            payment_deadline,
            session_id,
        )
        
        print(f"[PAYMENT] ✅ Pagamento registado: Sessão {session_id} | Valor: €{amount} | Prazo saída: {payment_deadline.isoformat()}")
    
    return JSONResponse({
        "session_id": session_id,
        "amount_paid": float(new_paid),
        "amount_due": float(amount_due),
        "status": new_status,
        "payment_method": method,
        "payment_amount": float(amount),
        "payment_deadline": payment_deadline.isoformat(),
        "message": "Pagamento efetuado! Tem 10 minutos para sair do parque."
    })


# ------------------------------------------------------------
# Sessions & Admin Endpoints
# ------------------------------------------------------------
@app.get("/api/sessions")
async def list_sessions(
    status: Optional[str] = None,
    plate: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List parking sessions with optional filters."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")
    
    # Build query with filters
    query = "SELECT id, plate, camera_id, spot, entry_time, exit_time, amount_due, amount_paid, status FROM public.parking_sessions WHERE 1=1"
    params = []
    param_idx = 1
    
    if status:
        query += f" AND status = ${param_idx}"
        params.append(status)
        param_idx += 1
    
    if plate:
        plate_norm = normalize_plate_text(plate)
        if plate_norm:
            query += f" AND plate ILIKE ${param_idx}"
            params.append(f"%{plate_norm}%")
            param_idx += 1
    
    query += f" ORDER BY entry_time DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    
    sessions = []
    for row in rows:
        sessions.append({
            "id": row["id"],
            "plate": row["plate"],
            "camera_id": row["camera_id"],
            "spot": row["spot"],
            "entry_time": row["entry_time"].isoformat() if row["entry_time"] else None,
            "exit_time": row["exit_time"].isoformat() if row["exit_time"] else None,
            "amount_due": float(row["amount_due"]) if row["amount_due"] else 0,
            "amount_paid": float(row["amount_paid"]) if row["amount_paid"] else 0,
            "status": row["status"],
        })
    
    return JSONResponse(sessions)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int):
    """Get detailed information about a specific session."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")
    
    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT id, plate, camera_id, entry_time, exit_time, 
                   amount_due, amount_paid, status, entry_image_url, exit_image_url
            FROM public.parking_sessions
            WHERE id = $1
            """,
            session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
        
        # Get payments for this session
        payments = await conn.fetch(
            "SELECT id, amount, method, paid_at FROM public.parking_payments WHERE session_id = $1 ORDER BY paid_at DESC",
            session_id
        )
    
    payment_list = [
        {
            "id": p["id"],
            "amount": float(p["amount"]),
            "method": p["method"],
            "paid_at": p["paid_at"].isoformat()
        }
        for p in payments
    ]
    
    return JSONResponse({
        "id": session["id"],
        "plate": session["plate"],
        "camera_id": session["camera_id"],
        "entry_time": session["entry_time"].isoformat() if session["entry_time"] else None,
        "exit_time": session["exit_time"].isoformat() if session["exit_time"] else None,
        "amount_due": float(session["amount_due"]) if session["amount_due"] else 0,
        "amount_paid": float(session["amount_paid"]) if session["amount_paid"] else 0,
        "status": session["status"],
        "entry_image_url": session["entry_image_url"],
        "exit_image_url": session["exit_image_url"],
        "payments": payment_list
    })


@app.get("/api/admin/stats")
async def admin_stats():
    """Get admin dashboard statistics."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel.")
    
    async with db_pool.acquire() as conn:
        # Total sessions
        total_sessions = await conn.fetchval("SELECT COUNT(*) FROM public.parking_sessions")
        
        # Active sessions (open status)
        active_sessions = await conn.fetchval("SELECT COUNT(*) FROM public.parking_sessions WHERE status = 'open'")
        
        # Total revenue (sum of amount_due for paid sessions)
        total_revenue = await conn.fetchval("SELECT COALESCE(SUM(amount_due), 0) FROM public.parking_sessions WHERE status = 'paid'")
        
        # Today's sessions
        today_sessions = await conn.fetchval(
            "SELECT COUNT(*) FROM public.parking_sessions WHERE entry_time::date = CURRENT_DATE"
        )
        
        # Average duration (in minutes) for completed sessions
        avg_duration = await conn.fetchval(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (exit_time - entry_time)) / 60)
            FROM public.parking_sessions
            WHERE exit_time IS NOT NULL AND entry_time IS NOT NULL
            """
        )
        
        # Recent sessions
        recent = await conn.fetch(
            """
            SELECT id, plate, spot, entry_time, exit_time, amount_due, status
            FROM public.parking_sessions
            ORDER BY entry_time DESC
            LIMIT 10
            """
        )
    
    recent_sessions = [
        {
            "id": r["id"],
            "plate": r["plate"],
            "spot": r["spot"],
            "entry_time": r["entry_time"].isoformat() if r["entry_time"] else None,
            "exit_time": r["exit_time"].isoformat() if r["exit_time"] else None,
            "amount_due": float(r["amount_due"]) if r["amount_due"] else 0,
            "status": r["status"]
        }
        for r in recent
    ]
    
    # Get current spot occupancy
    with g_lock:
        total_spots = len(g_spot_status)
        occupied_spots = sum(1 for spot in g_spot_status.values() if spot.get("occupied"))
    
    return JSONResponse({
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "total_revenue": float(total_revenue) if total_revenue else 0,
        "today_sessions": today_sessions,
        "avg_duration_minutes": float(avg_duration) if avg_duration else 0,
        "total_spots": total_spots,
        "occupied_spots": occupied_spots,
        "recent_sessions": recent_sessions
    })


@app.post("/api/sessions/{session_id}/simulate-payment")
async def simulate_payment(session_id: int, payload: PaymentPayload):
    """Simulate payment for a session (for academic purposes)."""
    # This just calls the existing payment endpoint
    return await api_payments(payload)


# ------------------------------------------------------------
# PAYMENT PAGE (Frontend para pagar estacionamento)
# ------------------------------------------------------------
@app.get("/payment")
def payment_page():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pagamento - Parking System</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: linear-gradient(135deg, #0f1115 0%, #1a1d23 100%); 
            color: #f2f2f2; 
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #3a8ef6; }
        .card {
            background: #1b1e24;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 15px;
            font-size: 18px;
            border: 2px solid #3a8ef6;
            border-radius: 8px;
            background: #0f1115;
            color: white;
            text-transform: uppercase;
        }
        button {
            padding: 15px 25px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s, background 0.2s;
        }
        button:hover { transform: scale(1.02); }
        .btn-primary { background: #3a8ef6; color: white; }
        .btn-success { background: #28a745; color: white; font-size: 18px; width: 100%; padding: 18px; }
        .btn-success:disabled { background: #555; cursor: not-allowed; }
        .session-info {
            display: none;
            margin-top: 20px;
        }
        .session-info.active { display: block; }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #333;
        }
        .info-label { color: #888; }
        .info-value { font-weight: bold; }
        .amount-due {
            font-size: 32px;
            text-align: center;
            color: #ff6b6b;
            margin: 20px 0;
        }
        .amount-due.paid { color: #28a745; }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
        }
        .status-open { background: #3a8ef6; }
        .status-paid { background: #28a745; }
        .status-closed { background: #6c757d; }
        .message {
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            text-align: center;
        }
        .message.success { background: rgba(40, 167, 69, 0.2); color: #28a745; }
        .message.error { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
        .payment-methods {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .payment-method {
            flex: 1;
            padding: 15px;
            border: 2px solid #333;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .payment-method:hover { border-color: #3a8ef6; }
        .payment-method.selected { border-color: #3a8ef6; background: rgba(58, 142, 246, 0.1); }
        .back-link { text-align: center; margin-top: 20px; }
        .back-link a { color: #3a8ef6; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>💳 Pagamento de Estacionamento</h1>
        
        <div class="card">
            <h3>Procurar minha sessao</h3>
            <div class="search-box">
                <input type="text" id="plateInput" placeholder="Matricula (ex: AB-12-CD)" maxlength="20">
                <button class="btn-primary" onclick="searchSession()">Procurar</button>
            </div>
            
            <div id="sessionInfo" class="session-info">
                <div class="info-row">
                    <span class="info-label">Matricula:</span>
                    <span class="info-value" id="infoPlate">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Entrada:</span>
                    <span class="info-value" id="infoEntry">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Vaga:</span>
                    <span class="info-value" id="infoSpot">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Tempo:</span>
                    <span class="info-value" id="infoTime">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Estado:</span>
                    <span class="info-value" id="infoStatus">-</span>
                </div>
                
                <div class="amount-due" id="amountDue">€0.00</div>
                
                <div id="paymentSection">
                    <h4 style="margin-bottom: 15px;">Metodo de pagamento:</h4>
                    <div class="payment-methods">
                        <div class="payment-method selected" data-method="card" onclick="selectMethod(this)">💳 Cartao</div>
                        <div class="payment-method" data-method="mbway" onclick="selectMethod(this)">📱 MBWay</div>
                        <div class="payment-method" data-method="cash" onclick="selectMethod(this)">💰 Numerario</div>
                    </div>
                    <button id="payBtn" class="btn-success" onclick="processPayment()">Pagar e Sair</button>
                </div>
                
                <div id="messageBox" class="message" style="display: none;"></div>
            </div>
        </div>
        
        <div class="back-link">
            <a href="/">← Voltar ao inicio</a>
        </div>
    </div>

    <script>
        let currentSession = null;
        let selectedMethod = 'card';
        
        function selectMethod(el) {
            document.querySelectorAll('.payment-method').forEach(m => m.classList.remove('selected'));
            el.classList.add('selected');
            selectedMethod = el.dataset.method;
        }
        
        async function searchSession() {
            const plate = document.getElementById('plateInput').value.toUpperCase().trim();
            if (!plate) {
                showMessage('Introduza a matricula', 'error');
                return;
            }
            
            try {
                const resp = await fetch(`/api/sessions?plate=${encodeURIComponent(plate)}&status=open&limit=1`);
                const data = await resp.json();
                
                if (!data.sessions || data.sessions.length === 0) {
                    showMessage('Nenhuma sessao aberta encontrada para esta matricula', 'error');
                    document.getElementById('sessionInfo').classList.remove('active');
                    return;
                }
                
                currentSession = data.sessions[0];
                displaySession(currentSession);
                
            } catch (err) {
                showMessage('Erro ao procurar sessao: ' + err.message, 'error');
            }
        }
        
        function displaySession(session) {
            document.getElementById('sessionInfo').classList.add('active');
            document.getElementById('infoPlate').textContent = session.plate;
            document.getElementById('infoEntry').textContent = new Date(session.entry_time).toLocaleString('pt-PT');
            document.getElementById('infoSpot').textContent = session.spot || 'Nao atribuida';
            
            // Calculate time
            const entry = new Date(session.entry_time);
            const now = new Date();
            const diffMs = now - entry;
            const hours = Math.floor(diffMs / 3600000);
            const mins = Math.floor((diffMs % 3600000) / 60000);
            document.getElementById('infoTime').textContent = `${hours}h ${mins}min`;
            
            // Calculate amount (1.50€/hour)
            const amount = Math.max(0.50, (diffMs / 3600000) * 1.50).toFixed(2);
            document.getElementById('amountDue').textContent = `€${amount}`;
            document.getElementById('amountDue').className = 'amount-due';
            
            // Status
            const statusEl = document.getElementById('infoStatus');
            if (session.amount_paid > 0) {
                statusEl.innerHTML = '<span class="status-badge status-paid">PAGO</span>';
                document.getElementById('amountDue').textContent = '✅ PAGO';
                document.getElementById('amountDue').className = 'amount-due paid';
                document.getElementById('payBtn').disabled = true;
                document.getElementById('payBtn').textContent = 'Ja pago - Pode sair';
            } else {
                statusEl.innerHTML = '<span class="status-badge status-open">AGUARDA PAGAMENTO</span>';
                document.getElementById('payBtn').disabled = false;
                document.getElementById('payBtn').textContent = 'Pagar €' + amount + ' e Sair';
            }
            
            hideMessage();
        }
        
        async function processPayment() {
            if (!currentSession) return;
            
            const btn = document.getElementById('payBtn');
            btn.disabled = true;
            btn.textContent = 'A processar...';
            
            // Calculate amount
            const entry = new Date(currentSession.entry_time);
            const diffMs = new Date() - entry;
            const amount = Math.max(0.50, (diffMs / 3600000) * 1.50);
            
            try {
                const resp = await fetch('/api/payments', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: currentSession.id,
                        amount: parseFloat(amount.toFixed(2)),
                        method: selectedMethod
                    })
                });
                
                const data = await resp.json();
                
                if (!resp.ok) {
                    throw new Error(data.detail || 'Erro no pagamento');
                }
                
                showMessage('✅ Pagamento efetuado! Tem 10 minutos para sair do parque.', 'success');
                document.getElementById('amountDue').textContent = '✅ PAGO';
                document.getElementById('amountDue').className = 'amount-due paid';
                btn.textContent = 'Pago - Pode sair!';
                document.getElementById('infoStatus').innerHTML = '<span class="status-badge status-paid">PAGO</span>';
                
            } catch (err) {
                showMessage('Erro: ' + err.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Tentar novamente';
            }
        }
        
        function showMessage(msg, type) {
            const box = document.getElementById('messageBox');
            box.textContent = msg;
            box.className = 'message ' + type;
            box.style.display = 'block';
        }
        
        function hideMessage() {
            document.getElementById('messageBox').style.display = 'none';
        }
        
        // Enter key to search
        document.getElementById('plateInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchSession();
        });
    </script>
</body>
</html>
    """)



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
            
            # Injetar pool no módulo de autenticação v2.0
            if set_auth_db_pool:
                set_auth_db_pool(db_pool)
                print("[INFO] Pool injetado no módulo de autenticação v2.0.")
            
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
