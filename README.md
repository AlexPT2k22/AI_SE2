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
PARKING_RATE_PER_HOUR=5.0      # tarifa padrao para calculo automatico
AUTO_CREATE_SESSION_FROM_OCR=true  # cria sessao automaticamente quando o OCR encontra placa
AUTO_CHARGE_ON_EXIT=true       # debita automaticamente ao fechar a sessao
AUTO_CHARGE_METHOD=auto_charge # texto armazenado em parking_payments.method nos debitos automaticos
PARKING_BILLING_MINUTE_STEP=1  # arredonda o tempo para multiplos de X minutos
PARKING_MINIMUM_FEE=0          # valor minimo a cobrar mesmo em estadias curtas
```

- Campos extras opcionais:
  - `SUPABASE_PUBLIC_BUCKET=true` quando quiser URLs diretas sem assinatura.
  - Ajuste `SUPABASE_BUCKET` caso use outro bucket.
  - `PARKING_RATE_PER_HOUR` define a tarifa em moeda local/hora utilizada nas contas automaticas perante saida.
  - `AUTO_CREATE_SESSION_FROM_OCR` quando `true` faz com que o endpoint `/licenseplate/upload` abra automaticamente uma sessao (caso nao exista outra aberta) sempre que uma placa valida for detectada.
  - `AUTO_CHARGE_ON_EXIT` habilita o debito automatico (criando um registro em `parking_payments` e atualizando `amount_paid`) assim que a saida e registrada.
  - `AUTO_CHARGE_METHOD` define o texto salvo no campo `method` quando o debito automatico acontece (padrao `auto_charge`).
  - `PARKING_BILLING_MINUTE_STEP` controla o arredondamento para cima no calculo de tempo (ex.: 15 = sempre cobrar blocos de 15 minutos).
  - `PARKING_MINIMUM_FEE` define uma tarifa minima para estacionamentos ultracurtos (ex.: 2.50 garante que ninguem pague menos que isso).
  - As tabelas `parking_sessions`, `parking_payments` **e `parking_event_log`** sao criadas automaticamente na inicializacao; verifique se o usuario tem permissao `CREATE TABLE`.
- `plate_country` eh um campo opcional enviado nos endpoints para diferenciar matriculas iguais de paises diferentes. Caso nao venha, o valor fica `null`.

## Executando a API
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Rotas
- `POST /licenseplate/upload`: upload e reconhecimento de placa a partir de uma imagem. Quando `AUTO_CREATE_SESSION_FROM_OCR=true` ele tambem chama automaticamente o fluxo de entrada (`/vehicles/entry`) para a placa detectada, retornando o objeto `session` na resposta. Parametros, workflow e erros seguem conforme descrito acima.
- `POST /vehicles/entry`: abre uma sessao de estacionamento (plate/camera/ticket). O `ticket_id` eh opcional; quando ausente a API gera um UUID garantido como unico. Retorna o `session_id` que identifica a sessao no banco.
- `POST /vehicles/{session_id}/exit`: finaliza a sessao calculando automaticamente o valor devido com base no tempo transcorrido. Atualiza o status para `pending_payment` ou `closed` quando nao ha saldo pendente.
- `POST /vehicles/{session_id}/payments`: registra um pagamento manual com o metodo/valor desejado e ajusta o status (`closed` quando o valor pago cobre o devido). Permite anexar `metadata` como JSON.
- `GET /vehicles/{session_id}`: devolve todos os detalhes da sessao incluindo historico de pagamentos.
- `GET /vehicles/open`: lista ate 100 sessoes com status `open` ou `pending_payment` para exibicao em dashboards.
- `POST /vehicles/exit-from-plate`: endpoint para automacao da cancela de saida. Recebe apenas `plate` (e opcionalmente `plate_country`) e fecha a sessao aberta correspondente sem precisar saber o `session_id`. Ideal para fluxo hands-free; quando `AUTO_CHARGE_ON_EXIT=true` gera o debito automaticamente usando o metodo configurado.

### Fluxo automatico 100% baseado em OCR
1. **Entrada:** o sensor cam chama `POST /licenseplate/upload` para reconhecer a placa. No retorno, utilize o `plate` detectado para chamar `POST /vehicles/entry` (enviando tambem `plate_country` se tiver) e guardar o `session_id` retornado se quiser correlacionar posteriormente.
2. **Associacao segura:** quando duas placas iguais existem em paises diferentes, informe `plate_country` (ex.: `PT`, `ES`, `BR-SP`). Esse campo fica persistido na tabela `parking_sessions`, evitando misturar veiculos distintos.
3. **Saida:** o sensor da cancela chama `POST /vehicles/exit-from-plate` com `plate` e `plate_country`. A API localiza automaticamente a sessao aberta mais antiga e a encerra, calculando o valor devido. Se `AUTO_CHARGE_ON_EXIT=true`, um registro de pagamento e criado automaticamente e `amount_paid` passa a refletir o debito efetivado.
4. **Pagamento manual (opcional):** caso prefira cobrar em caixa ou app, desative `AUTO_CHARGE_ON_EXIT` e use `POST /vehicles/{session_id}/payments` com o `session_id` retornado no passo 1 (ou consultado com `GET /vehicles/{session_id}`).

> Observacao: `session_id` eh apenas a chave primaria da sessao no Postgres. Ele e gerado automaticamente na entrada e disseminado nas respostas para integracoes que precisam manipular pagamentos ou relatórios. Para o fluxo basico da cancela nao eh necessario armazena-lo, pois o endpoint `/vehicles/exit-from-plate` ja faz o match por placa.

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
