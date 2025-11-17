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
cvzone
numpy
ultralytics
supabase
asyncpg
```
> Crie um `requirements.txt` com os pacotes acima ou instale diretamente via `pip install fastapi uvicorn[standard] python-multipart python-dotenv fast-alpr opencv-python cvzone numpy ultralytics supabase asyncpg`.
>
> **Importante:** o Ultralytics YOLO exige PyTorch. Instale a versao adequada para sua GPU/CPU seguindo [pytorch.org](https://pytorch.org/get-started/locally/).

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
- `parking/train_yolov11.py`: utilitario para treinar um detector YOLOv11 usando o dataset Roboflow incluso em `parking/parking lot.v1i.yolov11/`.

## Treinando o detector YOLOv11 para vagas
1. Configure o ambiente: `pip install -r requirements.txt` e instale PyTorch (GPU se disponivel).
2. O dataset Roboflow ja esta no repo em `parking/parking lot.v1i.yolov11/` com splits train/val/test descritos em `data.yaml`.
3. Rode o script:
   ```bash
   python parking/train_yolov11.py \
     --model yolo11n.pt \
     --epochs 150 \
     --imgsz 768 \
     --batch 16
   ```
   Isso cria um run em `runs/parking-yolo11/exp/` contendo pesos (`weights/best.pt`), graficos e logs.
4. Parametros uteis:
   - `--data`: use outro `data.yaml` se quiser expandir o dataset.
   - `--device cpu|0|0,1`: escolhe CPU ou GPU(s).
   - `--resume runs/.../weights/last.pt`: retoma um treinamento anterior.
   - `--project`/`--name`: personaliza onde salvar os artefatos.
5. Ao terminar, utilize `best.pt` como ponto de partida para inferencias ou exporte via `yolo export`/`ultralytics` conforme necessidade.

### Inferencia em video com o `best.pt`
1. Certifique-se de que o `best.pt` existe (ex.: `runs/parking-yolo11/exp2/weights/best.pt`).
2. Rode:
   ```bash
   python parking/predict_yolov11_video.py ^
     --weights runs/parking-yolo11/exp2/weights/best.pt ^
     --source caminho/do/video.mp4 ^
     --conf 0.25 ^
     --project runs/parking-yolo11/predicoes ^
     --name teste-video ^
     --window-width 900
   ```
   - `--source` aceita caminhos para videos (`.mp4`, `.avi`), webcam (`0`) ou pastas com imagens.
   - Os arquivos anotados sao salvos em `runs/parking-yolo11/predicoes/<name>/`.
   - Use `--show` para abrir uma janela com preview, `--window-width` para controlar o tamanho exibido e `--vid-stride 2` (ou mais) para pular frames em videos longos. Pressione `q` para fechar a janela.
3. O script escolhe automaticamente GPU se estiver disponivel; force CPU com `--device cpu`.

## Marcando vagas manualmente com OpenCV
Quando precisar definir manualmente as vagas usando 4 pontos, utilize `mark_parking_spots.py`.
```bash
python mark_parking_spots.py ^
  --source parking/frame_referencia.jpg ^
  --output data/parking_spots.json ^
  --label-prefix vaga ^
  --start-index 1
```
- Se `--source` for um video (`.mp4`, `.avi` etc.), use `--frame 150` para escolher o frame base.
- Clique ESQUERDO quatro vezes para formar uma vaga; clique DIREITO para desfazer o ultimo ponto.
- Atalhos: `s` salva, `z` remove a ultima vaga, `c` limpa os pontos atuais, `q` encerra.
- O JSON resultante inclui o caminho da midia, frame usado, dimensoes de referencia e a lista de vagas com os quatro pontos.

## Visualizando as vagas sobre o video
Para conferir se as vagas marcadas fazem sentido no video completo, use `visualize_spots_on_video.py`.
```bash
python visualize_spots_on_video.py ^
  --video parking/video.mp4 ^
  --spots parking_spots.json ^
  --output runs/parking-yolo11/overlays/video_spots.mp4 ^
  --window-width 1000 ^
  --codec avc1
```
- `--output` eh opcional; se definido, grava o video anotado no caminho informado.
- Caso o JSON tenha sido marcado em uma resolucao diferente da do video, o script ajusta automaticamente as coordenadas usando as dimensoes salvas (ou tenta inferir a partir do `source`).
- `--no-preview` desativa a janela (util quando estiver rodando em servidor sem GUI).
- `--alpha` controla a transparencia das vagas preenchidas (default 0.35).
- Use `--codec` para escolher o FourCC do video resultante. Por padrao o script tenta reutilizar o codec do video original; defina explicitamente (`avc1`, `mp4v`, `XVID`, etc.) se notar perda de qualidade ou incompatibilidade.
- Pressione `q` para encerrar o preview.

## Monitorando vagas com YOLO (ocupado x livre)
Use `monitor_parking_yolo.py` para rodar o `best.pt` (ou outro peso YOLO) em um video enquanto cruza as deteccoes com as vagas do `parking_spots.json`.
```bash
python monitor_parking_yolo.py ^
  --video parking/video.mp4 ^
  --spots parking_spots.json ^
  --weights runs/parking-yolo11/exp2/weights/best.pt ^
  --output runs/parking-yolo11/overlays/monitorado.mp4 ^
  --class-names car truck bus ^
  --overlap-threshold 0.2 ^
  --stabilize-frames 3 ^
  --window-width 1000 ^
  --summary-json runs/parking-yolo11/overlays/monitorado_summary.json
```
- Defina `--classes` (IDs) ou `--class-names` (texto) para limitar os objetos que contam como veículo. Ex.: no COCO `2=car`, `3=motorcycle`, `5=bus`, `7=truck` (0 e 1 são pessoa/bicicleta).
- `--overlap-threshold` estabelece a fração mínima da área da vaga coberta pelo bbox + centro do carro dentro da vaga para marcar como ocupada (default 0.15).
- `--stabilize-frames` suaviza trocas rápidas exigindo N frames consecutivos antes de confirmar um novo estado (0 desativa).
- `--summary-json` grava estatísticas por vaga (frames totais, frames ocupados e razão) além do vídeo. `--alpha`, `--codec`, `--no-preview`, `--device`, `--conf` e `--iou` seguem o mesmo padrão dos demais scripts.
- O vídeo resultante exibe cada vaga em verde (livre) ou vermelho (ocupada) com nome/estado, além dos bounding boxes detectados pelo YOLO.

## Dicas de operacao
- Certifique-se de que o bucket existe e que a role configurada no `SUPABASE_KEY` possui acesso de leitura/escrita.
- Quando `SUPABASE_PUBLIC_BUCKET=false`, a API devolve URLs assinadas com 1h de expiracao (ajuste `expires_in` em `upload_and_get_url` se precisar).
- Verifique se a tabela `parking_event_log` contem as colunas usadas no `INSERT` antes de subir a API em producao.
- Use GPUs apenas se tiver instalado os providers correspondentes; por padrao o `fast_alpr` esta configurado para CPU.

## Comandos
```
python mark_parking_spots.py --source frame.png --output parking_spots.json --label-prefix vaga --start-index 1

python visualize_spots_on_video.py --video video.mp4 --spots parking_spots.json --output video_spots.mp4 --codec mp4v

python monitor_parking_yolo.py --video video.mp4 --spots parking_spots.json --weights yolo11l.pt --classes 2 3 5 7 --overlap-threshold 0.2 --window-width 1920 --codec mp4v
```
