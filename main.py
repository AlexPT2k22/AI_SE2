from typing import Union, Any
import os
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fast_alpr import ALPR
from supabaseStorage import SupabaseStorageService
from dotenv import load_dotenv
import asyncpg

load_dotenv()

app = FastAPI()

def _normalize_confidence(value: Any) -> float | None:
    """Convert confidence values (scalar or iterable) into a float average."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple)):
        valid = [float(v) for v in value if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)
    return None


def serialize_alpr_result(result: Any) -> dict[str, Any]:
    """Map ALPRResult dataclasses to JSON-serializable dicts."""
    detection = getattr(result, "detection", None)
    ocr = getattr(result, "ocr", None)

    bbox = getattr(detection, "bounding_box", None) if detection else None
    detection_dict = (
        {
            "confidence": _normalize_confidence(getattr(detection, "confidence", None)),
            "bounding_box": {
                "x1": getattr(bbox, "x1", None),
                "y1": getattr(bbox, "y1", None),
                "x2": getattr(bbox, "x2", None),
                "y2": getattr(bbox, "y2", None),
            }
            if bbox
            else None,
        }
        if detection
        else None
    )

    ocr_conf_raw = getattr(ocr, "confidence", None) if ocr else None
    ocr_dict = (
        {
            "text": getattr(ocr, "text", None),
            "confidence": _normalize_confidence(ocr_conf_raw),
        }
        if ocr
        else None
    )

    return {"detection": detection_dict, "ocr": ocr_dict}

# ---------------- SUPABASE ----------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xxxx.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "parking-images")
SUPABASE_PUBLIC_BUCKET = os.getenv("SUPABASE_PUBLIC_BUCKET", "false").lower() == "true"

storage = SupabaseStorageService(
    supabase_url=SUPABASE_URL,
    supabase_key=SUPABASE_KEY,
    bucket_name=SUPABASE_BUCKET,
    public_bucket=SUPABASE_PUBLIC_BUCKET,
)

# ---------------- POSTGRES ---------------------------------
POSTGRES_URL = os.getenv("DATABASE_URL")

async def get_db():
    return await asyncpg.connect(POSTGRES_URL)

# ---------------- FAST ALPR --------------------------------
alpr = ALPR(
    detector_model="yolo-v9-s-608-license-plate-end2end",
    ocr_model="cct-s-v1-global-model",
    detector_providers=["CPUExecutionProvider"],
    ocr_device="cpu",
    ocr_providers=["CPUExecutionProvider"],
)

@app.get("/")
async def root():
    return {"message": "FastAPI ALPR Service is running."}


@app.post("/licenseplate/upload")
async def recognize_license_plate(
    file: UploadFile = File(...),
    camera_id: str = "default_cam",
):

    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Failed to decode image")

    alpr_results = alpr.predict(image)

    detected_plate = None
    ocr_conf = None
    det_conf = None

    if alpr_results:
        first = alpr_results[0] if isinstance(alpr_results, (list, tuple)) else alpr_results

        if first.ocr is not None:
            detected_plate = first.ocr.text
            ocr_conf = _normalize_confidence(first.ocr.confidence)

        if first.detection is not None:
            det_conf = _normalize_confidence(first.detection.confidence)

    plate_for_filename = detected_plate.replace(" ", "") if detected_plate else "unknown"

    try:
        image_url_or_signed = storage.upload_and_get_url(
            image_bytes=image_bytes,
            plate=plate_for_filename
        )
        file_path = f"{plate_for_filename}"
    except Exception as e:
        image_url_or_signed = None
        file_path = None
        print(f"[Error uploading to Supabase] {e}")


    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO parking_event_log
            (detected_plate, final_plate, det_confidence, ocr_confidence, image_path, camera_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            detected_plate,
            detected_plate,       
            det_conf,
            ocr_conf,
            image_url_or_signed,
            camera_id
        )
    finally:
        await db.close()

    serialized_results = [serialize_alpr_result(res) for res in alpr_results] if alpr_results else []
    return JSONResponse(
        content={
            "plate": detected_plate,
            "det_confidence": det_conf,
            "ocr_confidence": ocr_conf,
            "image_url": image_url_or_signed,
            "camera_id": camera_id,
            "alpr_raw": serialized_results,
        }
    )
