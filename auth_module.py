"""
Módulo de Autenticação - Sistema de Estacionamento TugaPark
Suporta:
- Registo com email/password
- Login com email/password OU matrícula/password
- JWT tokens
- Gestão de veículos
- Gestão de cartões de pagamento
- Controlo de acesso por role (admin/client)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import os
import jwt
import bcrypt
from pydantic import BaseModel, Field, EmailStr
from fastapi import HTTPException, Header
import asyncpg

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 dias

# Tarifa por hora
PARKING_RATE_PER_HOUR = float(os.getenv("PARKING_RATE_PER_HOUR", 1.50))
RESERVATION_FINE = 20.00  # Multa por reserva não usada


# =====================================================
# MODELOS PYDANTIC
# =====================================================

class RegisterPayload(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)  # bcrypt max 72 bytes
    full_name: str = Field(..., min_length=2, max_length=100)


class LoginPayload(BaseModel):
    identifier: str = Field(..., min_length=1)  # Email ou matrícula
    password: str = Field(..., min_length=1)


class VehiclePayload(BaseModel):
    plate: str = Field(..., min_length=1, max_length=20)
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    is_primary: bool = False


class PaymentMethodPayload(BaseModel):
    card_type: str = Field(..., pattern="^(visa|mastercard|amex|other)$")
    card_number: str = Field(..., min_length=16, max_length=19)  # Só guardamos últimos 4
    card_holder_name: str = Field(..., min_length=2)
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2024)
    is_default: bool = False
    auto_pay: bool = False  # TRUE = débito automático na saída


class ReservationPayload(BaseModel):
    spot: str = Field(..., min_length=1)
    plate: str = Field(..., min_length=1)
    reservation_date: str  # Formato: YYYY-MM-DD


# =====================================================
# FUNÇÕES DE PASSWORD (usando bcrypt diretamente)
# =====================================================

def hash_password(password: str) -> str:
    """Hash password com bcrypt."""
    # Truncar password a 72 bytes (limite do bcrypt)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar password."""
    try:
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False



# =====================================================
# FUNÇÕES JWT
# =====================================================

def generate_jwt_token(user_data: Dict[str, Any]) -> str:
    """Gerar JWT token."""
    payload = {
        **user_data,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verificar e decodificar JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "role": payload.get("role"),
        }
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_jwt_user(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    """Extrair user do header Authorization."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return verify_jwt_token(parts[1])


def require_auth(authorization: Optional[str]) -> Dict[str, Any]:
    """Requer autenticação - lança exceção se não autenticado."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return user


def require_admin(authorization: Optional[str]) -> Dict[str, Any]:
    """Requer role admin - lança exceção se não for admin."""
    user = require_auth(authorization)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user


# =====================================================
# FUNÇÕES DE NORMALIZAÇÃO
# =====================================================

def normalize_plate(plate: str) -> str:
    """Normalizar matrícula (UPPER, sem hífens/espaços)."""
    if not plate:
        return ""
    return "".join(ch for ch in plate.upper() if ch.isalnum())


# =====================================================
# FUNÇÕES DE BASE DE DADOS
# =====================================================

async def get_user_by_email(pool: asyncpg.Pool, email: str) -> Optional[Dict[str, Any]]:
    """Buscar utilizador por email."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, full_name, role FROM public.parking_users WHERE email = $1",
            email.lower()
        )
        if row:
            return dict(row)
    return None


async def get_user_by_plate(pool: asyncpg.Pool, plate_norm: str) -> Optional[Dict[str, Any]]:
    """Buscar utilizador por matrícula do veículo."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.password_hash, u.full_name, u.role
            FROM public.parking_users u
            JOIN public.parking_user_vehicles v ON u.id = v.user_id
            WHERE v.plate_norm = $1
            """,
            plate_norm
        )
        if row:
            return dict(row)
    return None


async def create_user(pool: asyncpg.Pool, email: str, password: str, full_name: str, role: str = "client") -> Dict[str, Any]:
    """Criar novo utilizador."""
    password_hash = hash_password(password)
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO public.parking_users (email, password_hash, full_name, role)
                VALUES ($1, $2, $3, $4)
                RETURNING id, email, full_name, role
                """,
                email.lower(),
                password_hash,
                full_name,
                role
            )
            return dict(row)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Email já registado")


async def get_user_vehicles(pool: asyncpg.Pool, user_id: int) -> List[Dict[str, Any]]:
    """Listar veículos do utilizador."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, plate, plate_norm, brand, model, color, is_primary, created_at
            FROM public.parking_user_vehicles
            WHERE user_id = $1
            ORDER BY is_primary DESC, created_at ASC
            """,
            user_id
        )
        return [dict(row) for row in rows]


async def add_vehicle(pool: asyncpg.Pool, user_id: int, payload: VehiclePayload) -> Dict[str, Any]:
    """Adicionar veículo ao utilizador."""
    plate_norm = normalize_plate(payload.plate)
    if not plate_norm:
        raise HTTPException(status_code=400, detail="Matrícula inválida")
    
    async with pool.acquire() as conn:
        # Se is_primary, desmarcar outros como não-primary
        if payload.is_primary:
            await conn.execute(
                "UPDATE public.parking_user_vehicles SET is_primary = FALSE WHERE user_id = $1",
                user_id
            )
        
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO public.parking_user_vehicles (user_id, plate, plate_norm, brand, model, color, is_primary)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, plate, plate_norm, brand, model, color, is_primary
                """,
                user_id,
                payload.plate.upper(),
                plate_norm,
                payload.brand,
                payload.model,
                payload.color,
                payload.is_primary
            )
            return dict(row)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Matrícula já registada")


async def delete_vehicle(pool: asyncpg.Pool, user_id: int, vehicle_id: int) -> bool:
    """Remover veículo do utilizador."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM public.parking_user_vehicles WHERE id = $1 AND user_id = $2",
            vehicle_id,
            user_id
        )
        return "DELETE 1" in result


async def get_user_payment_methods(pool: asyncpg.Pool, user_id: int) -> List[Dict[str, Any]]:
    """Listar métodos de pagamento do utilizador."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, card_type, card_last_four, card_holder_name, expiry_month, expiry_year, is_default, auto_pay, created_at
            FROM public.parking_user_payment_methods
            WHERE user_id = $1
            ORDER BY is_default DESC, created_at ASC
            """,
            user_id
        )
        return [dict(row) for row in rows]


async def add_payment_method(pool: asyncpg.Pool, user_id: int, payload: PaymentMethodPayload) -> Dict[str, Any]:
    """Adicionar método de pagamento ao utilizador."""
    # Extrair últimos 4 dígitos
    card_last_four = payload.card_number.replace(" ", "")[-4:]
    
    async with pool.acquire() as conn:
        # Se is_default, desmarcar outros
        if payload.is_default:
            await conn.execute(
                "UPDATE public.parking_user_payment_methods SET is_default = FALSE WHERE user_id = $1",
                user_id
            )
        
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO public.parking_user_payment_methods 
                    (user_id, card_type, card_last_four, card_holder_name, expiry_month, expiry_year, is_default, auto_pay)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, card_type, card_last_four, card_holder_name, expiry_month, expiry_year, is_default, auto_pay
                """,
                user_id,
                payload.card_type,
                card_last_four,
                payload.card_holder_name.upper(),
                payload.expiry_month,
                payload.expiry_year,
                payload.is_default,
                payload.auto_pay
            )
            return dict(row)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Cartão já registado")


async def delete_payment_method(pool: asyncpg.Pool, user_id: int, method_id: int) -> bool:
    """Remover método de pagamento do utilizador."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM public.parking_user_payment_methods WHERE id = $1 AND user_id = $2",
            method_id,
            user_id
        )
        return "DELETE 1" in result


async def get_default_payment_method(pool: asyncpg.Pool, user_id: int) -> Optional[Dict[str, Any]]:
    """Obter método de pagamento default do utilizador."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, card_type, card_last_four, card_holder_name
            FROM public.parking_user_payment_methods
            WHERE user_id = $1 AND is_default = TRUE
            """,
            user_id
        )
        return dict(row) if row else None


async def process_auto_payment(pool: asyncpg.Pool, session_id: int, user_id: int, amount: float) -> Dict[str, Any]:
    """Processar pagamento automático na saída."""
    payment_method = await get_default_payment_method(pool, user_id)
    if not payment_method:
        raise HTTPException(status_code=400, detail="Nenhum método de pagamento registado")
    
    async with pool.acquire() as conn:
        # Criar registo de pagamento
        payment_row = await conn.fetchrow(
            """
            INSERT INTO public.parking_payments 
                (session_id, user_id, payment_method_id, amount, payment_type, method)
            VALUES ($1, $2, $3, $4, 'parking', 'auto_debit')
            RETURNING id, amount, paid_at
            """,
            session_id,
            user_id,
            payment_method["id"],
            amount
        )
        
        # Atualizar sessão
        await conn.execute(
            """
            UPDATE public.parking_sessions 
            SET status = 'paid', amount_paid = $1, auto_payment_at = NOW(), payment_method_id = $2
            WHERE id = $3
            """,
            amount,
            payment_method["id"],
            session_id
        )
        
        return {
            "payment_id": payment_row["id"],
            "amount": float(payment_row["amount"]),
            "paid_at": payment_row["paid_at"].isoformat(),
            "card": f"**** **** **** {payment_method['card_last_four']}"
        }


async def create_notification(pool: asyncpg.Pool, user_id: int, title: str, body: str, 
                              notification_type: str, data: Optional[Dict] = None):
    """Criar notificação para utilizador."""
    import json
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO public.parking_notifications (user_id, title, body, notification_type, data)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            title,
            body,
            notification_type,
            json.dumps(data) if data else None
        )


async def get_user_notifications(pool: asyncpg.Pool, user_id: int, unread_only: bool = False) -> List[Dict[str, Any]]:
    """Listar notificações do utilizador."""
    async with pool.acquire() as conn:
        query = """
            SELECT id, title, body, notification_type, data, is_read, created_at
            FROM public.parking_notifications
            WHERE user_id = $1
        """
        if unread_only:
            query += " AND is_read = FALSE"
        query += " ORDER BY created_at DESC LIMIT 50"
        
        rows = await conn.fetch(query, user_id)
        return [dict(row) for row in rows]


async def mark_notification_read(pool: asyncpg.Pool, user_id: int, notification_id: int) -> bool:
    """Marcar notificação como lida."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE public.parking_notifications SET is_read = TRUE WHERE id = $1 AND user_id = $2",
            notification_id,
            user_id
        )
        return "UPDATE 1" in result


async def get_user_by_vehicle_plate(pool: asyncpg.Pool, plate_norm: str) -> Optional[Dict[str, Any]]:
    """Obter utilizador pelo veículo."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.full_name, u.role
            FROM public.parking_users u
            JOIN public.parking_user_vehicles v ON u.id = v.user_id
            WHERE v.plate_norm = $1
            """,
            plate_norm
        )
        return dict(row) if row else None


async def check_reservation_violation(pool: asyncpg.Pool, spot: str, plate_norm: str) -> Optional[Dict[str, Any]]:
    """Verificar se há violação de reserva."""
    from datetime import date
    async with pool.acquire() as conn:
        # Verificar se o spot tem reserva para hoje
        reservation = await conn.fetchrow(
            """
            SELECT r.*, u.id as owner_id, u.full_name as owner_name
            FROM public.parking_manual_reservations r
            JOIN public.parking_users u ON r.user_id = u.id
            WHERE r.spot = $1 AND r.reservation_date = $2
            """,
            spot,
            date.today()
        )
        
        if reservation:
            # Se a matrícula não é a da reserva, é violação
            if reservation["plate_norm"] != plate_norm:
                return {
                    "is_violation": True,
                    "reservation_owner_id": reservation["owner_id"],
                    "reservation_owner_name": reservation["owner_name"],
                    "reserved_plate": reservation["plate"],
                    "violator_plate": plate_norm,
                    "spot": spot
                }
            else:
                # Marcar reserva como usada
                await conn.execute(
                    "UPDATE public.parking_manual_reservations SET was_used = TRUE WHERE id = $1",
                    reservation["id"]
                )
        
        return None
