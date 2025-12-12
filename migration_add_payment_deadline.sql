-- Adicionar coluna payment_deadline à tabela parking_sessions
-- Execute este SQL no pgAdmin ou psql

ALTER TABLE public.parking_sessions 
ADD COLUMN IF NOT EXISTS payment_deadline TIMESTAMPTZ NULL;

-- Verificar se a coluna foi adicionada
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'parking_sessions' 
  AND column_name = 'payment_deadline';
