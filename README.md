# FastAPI ALPR Service

## Visao geral
- API em FastAPI que recebe imagens, executa OCR de placa com o pacote `fast_alpr` e salva o registro em PostgreSQL.
- As imagens processadas sao gravadas em um bucket Supabase Storage (publico ou privado) e tem a URL retornada na resposta.
- O endpoint exposto (`POST /licenseplate/upload`) valida a imagem, normaliza as confiancas de deteccao/OCR e devolve um payload JSON pronto para uso em dashboards.

## Fluxo do codigo
1. `main.py` carrega as variaveis de ambiente com `python-dotenv`, instancia o cliente `ALPR` e o servico de armazenamento.
2. O endpoint recebe o arquivo (`UploadFile`), valida o mime type e reconstrui a imagem com OpenCV.
3. `fast_alpr.ALPR.predict` gera deteccao (bounding box) e OCR; `serialize_alpr_result` transforma o retorno em dict serializavel.
4. O bytes original e enviado para o Supabase via `SupabaseStorageService.upload_and_get_url`, que decide entre URL publica ou assinada.
5. Os metadados (placa lida, camera, confianca, URL da imagem) sao persistidos na tabela `parking_event_log` de um Postgres acessado por `asyncpg`.
6. A resposta agrega tudo em um `JSONResponse`, incluindo o campo `alpr_raw` com o resultado completo da rede.

## Dependencias
### Software base
- Python 3.10+ com `pip`
- Conta Supabase com bucket configurado
- Banco PostgreSQL acessivel via URL unica (ex.: `postgresql://user:pwd@host:5432/db`)

### Pacotes Python principais
```
fastapi
uvicorn[standard]
python-multipart
python-dotenv
fast-alpr
opencv-python
numpy
supabase
asyncpg
```
> Crie um `requirements.txt` com os pacotes acima ou instale diretamente via `pip install fastapi uvicorn[standard] python-multipart python-dotenv fast-alpr opencv-python numpy supabase asyncpg`.

## Setup rapido
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install --upgrade pip
pip install fastapi uvicorn[standard] python-multipart python-dotenv fast-alpr opencv-python numpy supabase asyncpg
```

## Variaveis de ambiente
Crie um arquivo `.env` ou exporte antes de iniciar a API.
```
SUPABASE_URL=https://<sua-instancia>.supabase.co
SUPABASE_KEY=chave-service-role-ou-anon
SUPABASE_BUCKET=parking-images
SUPABASE_PUBLIC_BUCKET=false   # use true se o bucket for publico
DATABASE_URL=postgresql://user:senha@host:5432/db
```

Campos extras opcionais:
- `SUPABASE_PUBLIC_BUCKET=true` quando quiser URLs diretas sem assinatura.
- Ajuste `SUPABASE_BUCKET` caso use outro bucket.

## Executando a API
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Rotas
- `POST /licenseplate/upload`
  - **Query params**: `camera_id` (opcional, default `default_cam`) para identificar o ponto de captura.
  - **Body**: `multipart/form-data` com o campo `file` contendo a imagem (`Content-Type: image/jpeg|png`).
  - **Workflow**: valida o arquivo, roda `ALPR.predict`, faz upload da imagem para o Supabase e grava o evento em `parking_event_log`.
  - **Resposta 200**: JSON com `plate`, confiancas de deteccao/OCR, URL da imagem (`image_url` ou link assinado) e `alpr_raw` contendo o retorno completo do modelo.
  - **Erros comuns**:
    - `400`: arquivo vazio, nao imagem ou falha no decode do OpenCV.
    - `500`: problemas com Supabase, Postgres ou execucao do modelo.

## Teste do endpoint
```bash
curl -X POST "http://localhost:8000/licenseplate/upload?camera_id=gate-01" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@samples/carro.jpg"
```
Resposta esperada:
```json
{
  "plate": "ABC1234",
  "det_confidence": 0.91,
  "ocr_confidence": 0.88,
  "image_url": "https://supabase.../signed",
  "camera_id": "gate-01",
  "alpr_raw": [
    {
      "detection": {"confidence": 0.93, "bounding_box": {...}},
      "ocr": {"text": "ABC1234", "confidence": 0.88}
    }
  ]
}
```

## Estrutura dos modulos
- `main.py`: aplica o fluxo completo (valida entrada, roda ALPR, envia para Supabase e salva no Postgres).
- `supabaseStorage.py`: encapsula upload, geracao de URL publica/assinada e nomenclatura dos arquivos.
- `alpr.py`: script simples para testar o modelo localmente, util para validar se os modelos foram baixados corretamente.

## Dicas de operacao
- Certifique-se de que o bucket existe e que a role configurada no `SUPABASE_KEY` possui acesso de leitura/escrita.
- Quando `SUPABASE_PUBLIC_BUCKET=false`, a API devolve URLs assinadas com 1h de expiracao (ajuste `expires_in` em `upload_and_get_url` se precisar).
- Verifique se a tabela `parking_event_log` contem as colunas usadas no `INSERT` antes de subir a API em producao.
- Use GPUs apenas se tiver instalado os providers correspondentes; por padrao o `fast_alpr` esta configurado para CPU.
