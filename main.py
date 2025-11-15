from typing import Union, Any
import os
import uuid
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from fast_alpr import ALPR
from supabaseStorage import SupabaseStorageService
from dotenv import load_dotenv
import asyncpg
from asyncpg import exceptions as asyncpg_exc

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
PARKING_RATE_PER_HOUR = float(os.getenv("PARKING_RATE_PER_HOUR", "5.0"))
AUTO_CREATE_SESSION_FROM_OCR = os.getenv("AUTO_CREATE_SESSION_FROM_OCR", "true").lower() == "true"
AUTO_CHARGE_ON_EXIT = os.getenv("AUTO_CHARGE_ON_EXIT", "true").lower() == "true"
AUTO_CHARGE_METHOD = os.getenv("AUTO_CHARGE_METHOD", "auto_charge")
PARKING_BILLING_MINUTE_STEP = max(int(os.getenv("PARKING_BILLING_MINUTE_STEP", "1")), 1)
PARKING_MINIMUM_FEE = Decimal(str(os.getenv("PARKING_MINIMUM_FEE", "0")))

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


# ---------------- PARKING SESSIONS/PAYMENTS ----------------
class PlateIdentifier(BaseModel):
    """Base payload describing a license plate and optional country origin."""

    plate: str = Field(..., description="License plate detected by ALPR.")
    plate_country: str | None = Field(
        default=None,
        description="Optional ISO country/city identifier to differentiate identical plate numbers.",
    )


class VehicleEntryRequest(PlateIdentifier):
    """Payload required to open a parking session when a vehicle enters."""

    camera_id: str | None = Field(default=None, description="Camera identifier or lane name.")
    ticket_id: str | None = Field(default=None, description="Ticket or RFID identifier to prevent duplicates.")
    notes: str | None = Field(default=None, description="Optional free text annotation.")


class VehicleEntryResponse(BaseModel):
    """Standard representation of a parking session after entry."""

    session_id: int
    plate: str
    plate_country: str | None = None
    entry_time: datetime
    exit_time: datetime | None = None
    status: str
    camera_id: str | None = None
    ticket_id: str | None = None
    amount_due: float | None = None
    amount_paid: float | None = None
    notes: str | None = None


class VehicleExitRequest(BaseModel):
    """Information required to close a parking session at exit."""

    exit_time: datetime | None = Field(
        default=None, description="Optional exit timestamp. Defaults to now in UTC if not provided."
    )


class VehicleExitResponse(VehicleEntryResponse):
    """Parking session after exit has been registered."""


class VehiclePlateExitRequest(VehicleExitRequest):
    """Automation-friendly request allowing exit closure based solely on license plate."""

    plate: str = Field(..., description="Plate to match against open sessions.")
    plate_country: str | None = Field(
        default=None, description="Optional ISO/country info used to disambiguate equal plates."
    )


class PaymentRequest(BaseModel):
    """Payload describing a payment operation for a parking session."""

    amount: float = Field(..., gt=0, description="Value paid by the driver.")
    method: str = Field(..., description="Payment method (cash, pix, card...).")
    reference: str | None = Field(default=None, description="Optional external reference or transaction id.")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Any structured data to store alongside the payment (e.g. terminal info)."
    )


class PaymentRecord(BaseModel):
    """Representation of a persisted payment row."""

    payment_id: int
    session_id: int
    amount: float
    method: str
    reference: str | None = None
    paid_at: datetime
    metadata: dict[str, Any] | None = None


class PaymentResponse(BaseModel):
    """Response returned after a payment is registered."""

    payment: PaymentRecord
    session: VehicleEntryResponse


class ParkingSessionDetail(VehicleEntryResponse):
    """Parking session enriched with all payments attached to it."""

    payments: list[PaymentRecord] = Field(default_factory=list)


def _quantize_currency(value: Decimal) -> Decimal:
    """Round monetary values using bankers rounding with 2 decimal places."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_parking_fee(entry_time: datetime, exit_time: datetime, rate: float | None = None) -> Decimal:
    """Compute the parking fee based on the configured hourly rate."""
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)
    if exit_time.tzinfo is None:
        exit_time = exit_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = Decimal(str(max((exit_time - entry_time).total_seconds(), 0)))
    elapsed_minutes = elapsed_seconds / Decimal("60")

    minute_step = Decimal(str(PARKING_BILLING_MINUTE_STEP))
    if elapsed_minutes <= Decimal("0"):
        elapsed_minutes = minute_step

    blocks = (elapsed_minutes / minute_step).to_integral_value(rounding=ROUND_UP)
    rounded_minutes = blocks * minute_step

    rate_decimal = Decimal(str(rate if rate is not None else PARKING_RATE_PER_HOUR))
    rate_per_minute = rate_decimal / Decimal("60")
    raw_fee = rate_per_minute * rounded_minutes
    if PARKING_MINIMUM_FEE > 0:
        raw_fee = max(raw_fee, PARKING_MINIMUM_FEE)
    return _quantize_currency(raw_fee)


async def ensure_database_schema() -> None:
    """Create the minimal schema required for sessions and payments."""
    if not POSTGRES_URL:
        return

    db = await get_db()
    try:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS parking_event_log (
                id SERIAL PRIMARY KEY,
                detected_plate TEXT,
                final_plate TEXT,
                det_confidence NUMERIC(5,2),
                ocr_confidence NUMERIC(5,2),
                image_path TEXT,
                camera_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS parking_sessions (
                id SERIAL PRIMARY KEY,
                plate TEXT NOT NULL,
                plate_country TEXT,
                entry_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                exit_time TIMESTAMPTZ,
                camera_id TEXT,
                ticket_id TEXT UNIQUE,
                amount_due NUMERIC(10,2),
                amount_paid NUMERIC(10,2) DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'open',
                notes TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS parking_payments (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES parking_sessions(id) ON DELETE CASCADE,
                amount NUMERIC(10,2) NOT NULL,
                method TEXT NOT NULL,
                reference TEXT,
                paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata JSONB
            )
            """
        )
    finally:
        await db.close()


async def _fetch_session(db: asyncpg.Connection, session_id: int) -> asyncpg.Record | None:
    """Retrieve a parking session row by its id."""
    return await db.fetchrow(
        """
        SELECT id, plate, plate_country, entry_time, exit_time, camera_id, ticket_id, status,
               amount_due, amount_paid, notes
        FROM parking_sessions
        WHERE id = $1
        """,
        session_id,
    )


def _serialize_session(record: asyncpg.Record) -> dict[str, Any]:
    """Convert a parking session record into a serializable dict."""
    return {
        "session_id": record["id"],
        "plate": record["plate"],
        "plate_country": record["plate_country"],
        "entry_time": record["entry_time"],
        "exit_time": record["exit_time"],
        "status": record["status"],
        "camera_id": record["camera_id"],
        "ticket_id": record["ticket_id"],
        "amount_due": float(record["amount_due"]) if record["amount_due"] is not None else None,
        "amount_paid": float(record["amount_paid"]) if record["amount_paid"] is not None else None,
        "notes": record["notes"],
    }


def _serialize_payment(record: asyncpg.Record) -> dict[str, Any]:
    """Convert a parking payment record into a dict."""
    return {
        "payment_id": record["id"],
        "session_id": record["session_id"],
        "amount": float(record["amount"]),
        "method": record["method"],
        "reference": record["reference"],
        "paid_at": record["paid_at"],
        "metadata": record["metadata"],
    }


def normalize_plate(value: str | None) -> str | None:
    """Uppercase and trim plate strings for consistent comparison."""
    if not value:
        return None
    return value.strip().upper()


async def _insert_parking_session(
    db: asyncpg.Connection,
    plate: str,
    plate_country: str | None,
    camera_id: str | None,
    ticket_id: str,
    notes: str | None,
) -> asyncpg.Record:
    """Insert a row into parking_sessions using an existing DB connection."""
    return await db.fetchrow(
        """
        INSERT INTO parking_sessions (plate, plate_country, camera_id, ticket_id, notes)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, plate, plate_country, entry_time, exit_time, camera_id, ticket_id, status,
                  amount_due, amount_paid, notes
        """,
        plate,
        plate_country,
        camera_id,
        ticket_id,
        notes,
    )


async def ensure_session_for_plate(
    plate: str,
    plate_country: str | None = None,
    camera_id: str | None = None,
    notes: str | None = None,
) -> asyncpg.Record:
    """Create a parking session for the plate when none is open/pending."""
    normalized_plate = normalize_plate(plate)
    normalized_country = normalize_plate(plate_country)

    if not normalized_plate:
        raise ValueError("plate is required")

    db = await get_db()
    try:
        existing = await db.fetchrow(
            """
            SELECT id, plate, plate_country, entry_time, exit_time, camera_id, ticket_id, status,
                   amount_due, amount_paid, notes
            FROM parking_sessions
            WHERE plate = $1
              AND ($2::text IS NULL OR COALESCE(plate_country, '') = $2)
              AND status IN ('open', 'pending_payment')
            ORDER BY entry_time ASC
            LIMIT 1
            """,
            normalized_plate,
            normalized_country,
        )
        if existing:
            return existing

        ticket = str(uuid.uuid4())
        return await _insert_parking_session(
            db,
            normalized_plate,
            normalized_country,
            camera_id,
            ticket,
            notes,
        )
    finally:
        await db.close()


async def _insert_payment_and_update_session(
    db: asyncpg.Connection,
    session_id: int,
    amount: Decimal,
    method: str,
    reference: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[asyncpg.Record, asyncpg.Record]:
    """Persist a payment and update the related session totals."""
    payment = await db.fetchrow(
        """
        INSERT INTO parking_payments (session_id, amount, method, reference, metadata)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, session_id, amount, method, reference, paid_at, metadata
        """,
        session_id,
        amount,
        method,
        reference,
        json.dumps(metadata) if isinstance(metadata, dict) else metadata,
    )

    session = await db.fetchrow(
        """
        UPDATE parking_sessions
        SET amount_paid = COALESCE(amount_paid, 0) + $1,
            status = CASE
                WHEN amount_due IS NULL THEN 'closed'
                WHEN COALESCE(amount_paid, 0) + $1 >= amount_due THEN 'closed'
                ELSE 'pending_payment'
            END
        WHERE id = $2
        RETURNING id, plate, plate_country, entry_time, exit_time, camera_id, ticket_id, status,
                  amount_due, amount_paid, notes
        """,
        amount,
        session_id,
    )
    return payment, session


async def auto_charge_session_if_needed(
    db: asyncpg.Connection,
    session: asyncpg.Record,
    metadata: dict[str, Any] | None = None,
) -> asyncpg.Record:
    """Automatically register a payment when AUTO_CHARGE_ON_EXIT is enabled."""
    if not AUTO_CHARGE_ON_EXIT:
        return session

    amount_due = session["amount_due"]
    if amount_due is None:
        return session

    amount_paid = session["amount_paid"] or Decimal("0")
    due_decimal = Decimal(str(amount_due))
    paid_decimal = Decimal(str(amount_paid))
    outstanding = due_decimal - paid_decimal

    if outstanding <= 0:
        return session

    _, updated = await _insert_payment_and_update_session(
        db,
        session["id"],
        _quantize_currency(outstanding),
        AUTO_CHARGE_METHOD,
        reference="auto_exit_charge",
        metadata=metadata or {"source": "auto_exit"},
    )
    return updated


@app.on_event("startup")
async def _startup() -> None:
    """Ensure database schema exists when the API boots."""
    await ensure_database_schema()

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
    auto_session = None
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

    if detected_plate and AUTO_CREATE_SESSION_FROM_OCR:
        try:
            auto_session = await ensure_session_for_plate(detected_plate, camera_id=camera_id)
        except Exception as exc:
            print(f"[Auto session creation failed] {exc}")

    serialized_results = [serialize_alpr_result(res) for res in alpr_results] if alpr_results else []
    payload = {
        "plate": detected_plate,
        "det_confidence": det_conf,
        "ocr_confidence": ocr_conf,
        "image_url": image_url_or_signed,
        "camera_id": camera_id,
        "alpr_raw": serialized_results,
        "session": _serialize_session(auto_session) if auto_session else None,
    }
    return JSONResponse(content=jsonable_encoder(payload))


@app.post("/vehicles/entry", response_model=VehicleEntryResponse)
async def register_vehicle_entry(payload: VehicleEntryRequest) -> VehicleEntryResponse:
    """Create a parking session when a vehicle crosses the entry gate."""
    db = await get_db()
    normalized_plate = normalize_plate(payload.plate)
    normalized_country = normalize_plate(payload.plate_country)
    ticket = payload.ticket_id or str(uuid.uuid4())
    try:
        record = await _insert_parking_session(
            db,
            normalized_plate,
            normalized_country,
            payload.camera_id,
            ticket,
            payload.notes,
        )
    except asyncpg_exc.UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="ticket_id already registered") from exc
    finally:
        await db.close()

    return VehicleEntryResponse(**_serialize_session(record))


@app.post("/vehicles/{session_id}/exit", response_model=VehicleExitResponse)
async def register_vehicle_exit(session_id: int, payload: VehicleExitRequest) -> VehicleExitResponse:
    """Mark the exit of a vehicle and calculate the amount due automatically."""
    db = await get_db()
    try:
        session = await _fetch_session(db, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Parking session not found")
        if session["status"] == "closed":
            raise HTTPException(status_code=400, detail="Parking session already closed")

        exit_at = payload.exit_time or datetime.now(timezone.utc)
        amount_due = calculate_parking_fee(session["entry_time"], exit_at)

        updated = await db.fetchrow(
            """
            UPDATE parking_sessions
            SET exit_time = $1,
                amount_due = $2,
                status = CASE
                    WHEN COALESCE(amount_paid, 0) >= $2 THEN 'closed'
                    ELSE 'pending_payment'
                END
            WHERE id = $3
            RETURNING id, plate, plate_country, entry_time, exit_time, camera_id, ticket_id, status,
                      amount_due, amount_paid, notes
            """,
            exit_at,
            amount_due,
            session_id,
        )
        updated = await auto_charge_session_if_needed(
            db,
            updated,
            metadata={"source": "auto_exit", "camera_id": session["camera_id"]},
        )
    finally:
        await db.close()

    return VehicleExitResponse(**_serialize_session(updated))


@app.post("/vehicles/{session_id}/payments", response_model=PaymentResponse)
async def register_vehicle_payment(session_id: int, payload: PaymentRequest) -> PaymentResponse:
    """Persist a payment and update the related parking session."""
    db = await get_db()
    try:
        session = await _fetch_session(db, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Parking session not found")

        amount_decimal = _quantize_currency(Decimal(str(payload.amount)))
        payment, updated = await _insert_payment_and_update_session(
            db,
            session_id,
            amount_decimal,
            payload.method,
            payload.reference,
            payload.metadata,
        )
    finally:
        await db.close()

    return PaymentResponse(payment=PaymentRecord(**_serialize_payment(payment)), session=VehicleEntryResponse(**_serialize_session(updated)))


@app.get("/vehicles/open", response_model=list[VehicleEntryResponse])
async def list_open_sessions(limit: int = 100) -> list[VehicleEntryResponse]:
    """List ongoing or pending-payment sessions, newest entries last."""
    db = await get_db()
    try:
        rows = await db.fetch(
            """
            SELECT id, plate, entry_time, exit_time, camera_id, ticket_id, status,
                   amount_due, amount_paid, notes, plate_country
            FROM parking_sessions
            WHERE status IN ('open', 'pending_payment')
            ORDER BY entry_time ASC
            LIMIT $1
            """,
            limit,
        )
    finally:
        await db.close()

    return [VehicleEntryResponse(**_serialize_session(row)) for row in rows]


@app.get("/vehicles/{session_id}", response_model=ParkingSessionDetail)
async def get_parking_session(session_id: int) -> ParkingSessionDetail:
    """Return all details for a specific parking session."""
    db = await get_db()
    try:
        session = await _fetch_session(db, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Parking session not found")

        payments = await db.fetch(
            """
            SELECT id, session_id, amount, method, reference, paid_at, metadata
            FROM parking_payments
            WHERE session_id = $1
            ORDER BY paid_at ASC
            """,
            session_id,
        )
    finally:
        await db.close()

    serialized = _serialize_session(session)
    serialized["payments"] = [_serialize_payment(p) for p in payments]
    return ParkingSessionDetail(**serialized)


@app.post("/vehicles/exit-from-plate", response_model=VehicleExitResponse)
async def register_exit_from_plate(payload: VehiclePlateExitRequest) -> VehicleExitResponse:
    """Automation endpoint to close a session using only plate and optional country."""
    normalized_plate = normalize_plate(payload.plate)
    normalized_country = normalize_plate(payload.plate_country)

    db = await get_db()
    session = None
    try:
        session = await db.fetchrow(
            """
            SELECT id
            FROM parking_sessions
            WHERE plate = $1
              AND ($2::text IS NULL OR COALESCE(plate_country, '') = $2)
              AND status IN ('open', 'pending_payment')
            ORDER BY entry_time ASC
            LIMIT 1
            """,
            normalized_plate,
            normalized_country,
        )
    finally:
        await db.close()

    if session is None:
        raise HTTPException(status_code=404, detail="Open session not found for plate")

    exit_payload = VehicleExitRequest(exit_time=payload.exit_time)
    return await register_vehicle_exit(session["id"], exit_payload)
