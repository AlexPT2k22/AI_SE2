ALTER TABLE public.parking_sessions 
ADD COLUMN IF NOT EXISTS entry_image_url TEXT NULL,
ADD COLUMN IF NOT EXISTS exit_image_url TEXT NULL;