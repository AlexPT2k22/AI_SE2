#!/usr/bin/env python3
"""
Script para testar a conexão à base de dados PostgreSQL/Supabase.
Uso: python test_db_connection.py
"""
import os
import asyncio
from dotenv import load_dotenv
import asyncpg

async def test_connection():
 # Carregar variáveis de ambiente do .env
 load_dotenv()
 
 database_url = os.getenv("DATABASE_URL")
 
 if not database_url:
 print("[ERRO] DATABASE_URL nao esta definida no arquivo .env")
 print("\nAdicione ao seu .env:")
 print('DATABASE_URL="postgresql://user:password@host:port/database"')
 return False
 
 print(f"[OK] DATABASE_URL encontrada")
 print(f" Tentando conectar a: {database_url[:30]}...")
 
 try:
 # Tentar criar um pool de conexões
 pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
 print("[OK] Pool de conexoes criado com sucesso")
 
 # Testar uma query simples
 async with pool.acquire() as conn:
 version = await conn.fetchval("SELECT version()")
 print(f"[OK] Conexao bem sucedida!")
 print(f" PostgreSQL version: {version[:50]}...")
 
 # Verificar tabelas necessárias
 tables = await conn.fetch("""
 SELECT table_name 
 FROM information_schema.tables 
 WHERE table_schema = 'public' 
 AND table_name IN ('parking_sessions', 'parking_payments', 'parking_web_users', 'parking_manual_reservations')
 ORDER BY table_name
 """)
 
 print(f"\n[OK] Tabelas encontradas ({len(tables)}/4):")
 for row in tables:
 print(f" - {row['table_name']}")
 
 missing_tables = set(['parking_sessions', 'parking_payments', 'parking_web_users', 'parking_manual_reservations']) - {row['table_name'] for row in tables}
 if missing_tables:
 print(f"\n[AVISO] Tabelas em falta: {', '.join(missing_tables)}")
 print(" Execute o script tables.txt para criar as tabelas")
 
 await pool.close()
 print("\n[SUCESSO] TUDO OK! A base de dados esta configurada corretamente.")
 return True
 
 except asyncpg.InvalidPasswordError:
 print("[ERRO] Senha invalida")
 return False
 except asyncpg.InvalidCatalogNameError:
 print("[ERRO] Base de dados nao existe")
 return False
 except Exception as e:
 print(f"[ERRO] {type(e).__name__}: {e}")
 return False

if __name__ == "__main__":
 success = asyncio.run(test_connection())
 exit(0 if success else 1)

