"""
Rotas de Autenticação - Sistema de Estacionamento TugaPark v2.0

Endpoints:
- POST /api/auth/register     - Registo com email/password
- POST /api/auth/login        - Login (email ou matrícula + password)
- GET  /api/auth/me           - Dados do utilizador autenticado
- GET  /api/user/vehicles     - Listar veículos
- POST /api/user/vehicles     - Adicionar veículo
- DELETE /api/user/vehicles/{id} - Remover veículo
- GET  /api/user/payment-methods - Listar cartões
- POST /api/user/payment-methods - Adicionar cartão
- DELETE /api/user/payment-methods/{id} - Remover cartão
- GET  /api/user/notifications - Listar notificações
- POST /api/user/notifications/{id}/read - Marcar como lida
- POST /api/reservations      - Criar reserva
"""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from datetime import date, datetime
import asyncpg

from auth_module import (
    RegisterPayload, LoginPayload, VehiclePayload, PaymentMethodPayload, ReservationPayload,
    get_user_by_email, get_user_by_plate, create_user, verify_password, generate_jwt_token,
    get_jwt_user, require_auth, require_admin, normalize_plate,
    get_user_vehicles, add_vehicle, delete_vehicle,
    get_user_payment_methods, add_payment_method, delete_payment_method,
    get_user_notifications, mark_notification_read, create_notification
)

router = APIRouter()

# Referência ao pool de BD (será injetada pelo main.py)
db_pool: Optional[asyncpg.Pool] = None
_refresh_reservations_callback = None

def set_db_pool(pool: asyncpg.Pool):
    """Injetar o pool de BD."""
    global db_pool
    db_pool = pool

def set_refresh_reservations_callback(callback):
    """Define o callback para atualizar o cache de reservas."""
    global _refresh_reservations_callback
    _refresh_reservations_callback = callback

async def _trigger_reservations_refresh():
    """Chama o callback para atualizar o cache de reservas."""
    if _refresh_reservations_callback:
        try:
            await _refresh_reservations_callback()
        except Exception as e:
            print(f"[WARN] Erro ao atualizar cache de reservas: {e}")


# =====================================================
# AUTENTICAÇÃO
# =====================================================

@router.post("/api/auth/register")
async def register(payload: RegisterPayload):
    """Registar novo utilizador com email e password."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    # Verificar se email já existe
    existing = await get_user_by_email(db_pool, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email já registado")
    
    # Criar utilizador
    user = await create_user(db_pool, payload.email, payload.password, payload.full_name)
    
    # Gerar token
    token = generate_jwt_token({
        "user_id": user["id"],
        "email": user["email"],
        "name": user["full_name"],
        "role": user["role"]
    })
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["full_name"],
            "role": user["role"]
        }
    }


@router.post("/api/auth/login")
async def login(payload: LoginPayload):
    """
    Login com email OU matrícula + password.
    - Se identifier contém '@', é email
    - Senão, é matrícula
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    identifier = payload.identifier.strip()
    password = payload.password
    
    # Determinar se é email ou matrícula
    if "@" in identifier:
        # Login por email
        user = await get_user_by_email(db_pool, identifier)
        if not user:
            raise HTTPException(status_code=401, detail="Email ou password incorretos")
    else:
        # Login por matrícula
        plate_norm = normalize_plate(identifier)
        user = await get_user_by_plate(db_pool, plate_norm)
        if not user:
            raise HTTPException(status_code=401, detail="Matrícula não registada")
    
    # Verificar password
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Password incorreta")
    
    # Gerar token
    token = generate_jwt_token({
        "user_id": user["id"],
        "email": user["email"],
        "name": user["full_name"],
        "role": user["role"]
    })
    
    # Obter veículos
    vehicles = await get_user_vehicles(db_pool, user["id"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["full_name"],
            "role": user["role"],
            "vehicles": vehicles
        }
    }


@router.get("/api/auth/me")
async def get_me(authorization: Optional[str] = Header(None)):
    """Obter dados do utilizador autenticado."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    
    # Obter dados completos
    vehicles = await get_user_vehicles(db_pool, user["user_id"])
    payment_methods = await get_user_payment_methods(db_pool, user["user_id"])
    
    return {
        "id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "vehicles": vehicles,
        "payment_methods": payment_methods
    }


# =====================================================
# VEÍCULOS
# =====================================================

@router.get("/api/user/vehicles")
async def list_vehicles(authorization: Optional[str] = Header(None)):
    """Listar veículos do utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    vehicles = await get_user_vehicles(db_pool, user["user_id"])
    return {"vehicles": vehicles}


@router.post("/api/user/vehicles")
async def create_vehicle(payload: VehiclePayload, authorization: Optional[str] = Header(None)):
    """Adicionar veículo ao utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    vehicle = await add_vehicle(db_pool, user["user_id"], payload)
    return {"vehicle": vehicle}


@router.delete("/api/user/vehicles/{vehicle_id}")
async def remove_vehicle(vehicle_id: int, authorization: Optional[str] = Header(None)):
    """Remover veículo do utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    success = await delete_vehicle(db_pool, user["user_id"], vehicle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return {"message": "Veículo removido"}


# =====================================================
# MÉTODOS DE PAGAMENTO
# =====================================================

@router.get("/api/user/payment-methods")
async def list_payment_methods(authorization: Optional[str] = Header(None)):
    """Listar métodos de pagamento do utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    methods = await get_user_payment_methods(db_pool, user["user_id"])
    return {"payment_methods": methods}


@router.post("/api/user/payment-methods")
async def create_payment_method(payload: PaymentMethodPayload, authorization: Optional[str] = Header(None)):
    """Adicionar método de pagamento ao utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    method = await add_payment_method(db_pool, user["user_id"], payload)
    return {"payment_method": method}


@router.delete("/api/user/payment-methods/{method_id}")
async def remove_payment_method(method_id: int, authorization: Optional[str] = Header(None)):
    """Remover método de pagamento do utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    success = await delete_payment_method(db_pool, user["user_id"], method_id)
    if not success:
        raise HTTPException(status_code=404, detail="Método de pagamento não encontrado")
    return {"message": "Método de pagamento removido"}


# =====================================================
# NOTIFICAÇÕES
# =====================================================

@router.get("/api/user/notifications")
async def list_notifications(unread_only: bool = False, authorization: Optional[str] = Header(None)):
    """Listar notificações do utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    notifications = await get_user_notifications(db_pool, user["user_id"], unread_only)
    return {"notifications": notifications}


@router.post("/api/user/notifications/{notification_id}/read")
async def mark_as_read(notification_id: int, authorization: Optional[str] = Header(None)):
    """Marcar notificação como lida."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    success = await mark_notification_read(db_pool, user["user_id"], notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    return {"message": "Notificação marcada como lida"}


# =====================================================
# RESERVAS
# =====================================================

@router.post("/api/reservations")
async def create_reservation(payload: ReservationPayload, authorization: Optional[str] = Header(None)):
    """
    Criar reserva de vaga.
    Só permite reservas para hoje ou amanhã.
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    
    # Validar data
    try:
        reservation_date = datetime.strptime(payload.reservation_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
    
    today = date.today()
    tomorrow = today + __import__("datetime").timedelta(days=1)
    
    if reservation_date < today:
        raise HTTPException(status_code=400, detail="Não é possível reservar para datas passadas")
    
    if reservation_date > tomorrow:
        raise HTTPException(status_code=400, detail="Só é possível reservar para hoje ou amanhã")
    
    # Normalizar matrícula
    plate_norm = normalize_plate(payload.plate)
    if not plate_norm:
        raise HTTPException(status_code=400, detail="Matrícula inválida")
    
    # Verificar se o utilizador tem este veículo
    vehicles = await get_user_vehicles(db_pool, user["user_id"])
    user_plates = [v["plate_norm"] for v in vehicles]
    if plate_norm not in user_plates:
        raise HTTPException(status_code=400, detail="Esta matrícula não pertence à sua conta")
    
    async with db_pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO public.parking_manual_reservations 
                    (user_id, spot, plate, plate_norm, reservation_date)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, spot, plate, reservation_date, created_at
                """,
                user["user_id"],
                payload.spot,
                payload.plate.upper(),
                plate_norm,
                reservation_date
            )
            
            # Atualizar cache de reservas no main.py
            await _trigger_reservations_refresh()
            
            return {
                "reservation": {
                    "id": row["id"],
                    "spot": row["spot"],
                    "plate": row["plate"],
                    "reservation_date": row["reservation_date"].isoformat(),
                    "created_at": row["created_at"].isoformat()
                },
                "message": f"Reserva criada para {row['spot']} no dia {row['reservation_date']}"
            }
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=400, detail="Este lugar já está reservado para esta data")
            raise HTTPException(status_code=500, detail=f"Erro ao criar reserva: {str(e)}")


@router.get("/api/reservations")
async def list_reservations(authorization: Optional[str] = Header(None)):
    """Listar reservas do utilizador."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, spot, plate, reservation_date, was_used, fine_applied, created_at
            FROM public.parking_manual_reservations
            WHERE user_id = $1
            ORDER BY reservation_date DESC
            """,
            user["user_id"]
        )
        
        return {
            "reservations": [
                {
                    "id": row["id"],
                    "spot": row["spot"],
                    "plate": row["plate"],
                    "reservation_date": row["reservation_date"].isoformat(),
                    "was_used": row["was_used"],
                    "fine_applied": row["fine_applied"],
                    "created_at": row["created_at"].isoformat()
                }
                for row in rows
            ]
        }


@router.delete("/api/reservations/{spot}")
async def cancel_reservation(spot: str, authorization: Optional[str] = Header(None)):
    """
    Cancelar reserva por nome da vaga.
    Só é possível cancelar nas primeiras 2 horas após criar a reserva.
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_auth(authorization)
    
    # Prazo para cancelamento: 2 horas após criação
    CANCELLATION_WINDOW_HOURS = 2
    
    async with db_pool.acquire() as conn:
        # Verificar se a reserva existe e pertence ao utilizador
        row = await conn.fetchrow(
            """
            SELECT id, reservation_date, created_at 
            FROM public.parking_manual_reservations 
            WHERE spot = $1 AND user_id = $2
            """,
            spot,
            user["user_id"]
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Reserva não encontrada")
        
        # Verificar se ainda está dentro do prazo de cancelamento (2 horas)
        created_at = row["created_at"]
        now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
        time_since_creation = now - created_at
        hours_since_creation = time_since_creation.total_seconds() / 3600
        
        if hours_since_creation > CANCELLATION_WINDOW_HOURS:
            raise HTTPException(
                status_code=400, 
                detail=f"Prazo de cancelamento expirado. Só pode cancelar nas primeiras {CANCELLATION_WINDOW_HOURS} horas após criar a reserva."
            )
        
        # Cancelar
        await conn.execute(
            "DELETE FROM public.parking_manual_reservations WHERE id = $1",
            row["id"]
        )
        
        # Atualizar cache de reservas no main.py
        await _trigger_reservations_refresh()
        
        return {"message": "Reserva cancelada com sucesso", "spot": spot}


# =====================================================
# SESSÕES DO UTILIZADOR
# =====================================================

@router.get("/api/user/sessions")
async def list_user_sessions(
    status: Optional[str] = None,
    limit: int = 50,
    authorization: Optional[str] = Header(None)
):
    """Listar sessões do utilizador autenticado."""
    user = get_jwt_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Base de dados indisponivel")
    
    async with db_pool.acquire() as conn:
        # Filtrar sessões pelo user_id
        if status:
            rows = await conn.fetch(
                """
                SELECT id, plate, spot, entry_time, exit_time, amount_due, amount_paid, status
                FROM public.parking_sessions
                WHERE user_id = $1 AND status = $2
                ORDER BY entry_time DESC
                LIMIT $3
                """,
                user["user_id"],
                status,
                limit
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, plate, spot, entry_time, exit_time, amount_due, amount_paid, status
                FROM public.parking_sessions
                WHERE user_id = $1
                ORDER BY entry_time DESC
                LIMIT $2
                """,
                user["user_id"],
                limit
            )
    
    sessions = []
    for row in rows:
        sessions.append({
            "id": row["id"],
            "plate": row["plate"],
            "spot": row["spot"],
            "entry_time": row["entry_time"].isoformat() if row["entry_time"] else None,
            "exit_time": row["exit_time"].isoformat() if row["exit_time"] else None,
            "amount_due": float(row["amount_due"]) if row["amount_due"] else 0,
            "amount_paid": float(row["amount_paid"]) if row["amount_paid"] else 0,
            "status": row["status"]
        })
    
    return {"sessions": sessions}


# =====================================================
# ADMIN ONLY - ESTATÍSTICAS
# =====================================================

@router.get("/api/admin/stats")
async def get_admin_stats(authorization: Optional[str] = Header(None)):
    """Estatísticas do estacionamento (apenas admin)."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_admin(authorization)
    
    async with db_pool.acquire() as conn:
        # Total de utilizadores
        users_count = await conn.fetchval("SELECT COUNT(*) FROM public.parking_users WHERE role = 'client'")
        
        # Sessões hoje
        sessions_today = await conn.fetchval(
            "SELECT COUNT(*) FROM public.parking_sessions WHERE DATE(entry_time) = CURRENT_DATE"
        )
        
        # Receita hoje
        revenue_today = await conn.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM public.parking_payments WHERE DATE(paid_at) = CURRENT_DATE"
        ) or 0
        
        # Reservas hoje
        reservations_today = await conn.fetchval(
            "SELECT COUNT(*) FROM public.parking_manual_reservations WHERE reservation_date = CURRENT_DATE"
        )
        
        # Multas hoje
        fines_today = await conn.fetchval(
            """
            SELECT COUNT(*) FROM public.parking_payments 
            WHERE payment_type = 'reservation_fine' AND DATE(paid_at) = CURRENT_DATE
            """
        )
        
        return {
            "users_count": users_count,
            "sessions_today": sessions_today,
            "revenue_today": float(revenue_today),
            "reservations_today": reservations_today,
            "fines_today": fines_today
        }


@router.get("/api/admin/users")
async def list_users(authorization: Optional[str] = Header(None)):
    """Listar todos os utilizadores (apenas admin)."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de dados indisponível")
    
    user = require_admin(authorization)
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.id, u.email, u.full_name, u.role, u.created_at,
                   (SELECT COUNT(*) FROM public.parking_user_vehicles WHERE user_id = u.id) as vehicles_count,
                   (SELECT COUNT(*) FROM public.parking_sessions WHERE user_id = u.id) as sessions_count
            FROM public.parking_users u
            ORDER BY u.created_at DESC
            """
        )
        
        return {
            "users": [
                {
                    "id": row["id"],
                    "email": row["email"],
                    "name": row["full_name"],
                    "role": row["role"],
                    "created_at": row["created_at"].isoformat(),
                    "vehicles_count": row["vehicles_count"],
                    "sessions_count": row["sessions_count"]
                }
                for row in rows
            ]
        }
