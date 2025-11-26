# Parking Monitor – FastAPI + ALPR + Reservas

Monitor completo de estacionamento com FastAPI: alimenta‑se de um vídeo/stream, corta cada vaga, classifica com uma CNN, roda ALPR apenas nas vagas reservadas e publica tudo via WebSocket/HTTP. O frontend embutido expõe páginas para acompanhar o fluxo em tempo real, reservar vagas e um painel admin que mostra vídeo, matrículas e eventos do ALPR.

---

## 1. Pré‑requisitos

| Item | Detalhes |
| --- | --- |
| Python | 3.10+ (virtualenv recomendado) |
| Pip packages | ver `requirements.txt` (`fastapi`, `uvicorn[standard]`, `python-dotenv`, `opencv-python`, `torch/torchvision`, `fast-alpr[onnx]`, `asyncpg`, etc.) |
| Vídeo/modelos | `video.mp4`, `parking_spots.json`, `spot_classifier.pth`, pesos YOLO opcionais |
| PostgreSQL | `DATABASE_URL` apontando para o schema `public` (tabelas em `tables.txt`) |
| Outros | Opcional: Supabase/ALPR externos se quiser reaproveitar scripts antigos |

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install --upgrade pip
pip install -r requirements.txt
```

Principais variáveis de ambiente (configure em `.env`):

```
SUPABASE_URL=url do supabase
SUPABASE_KEY=key do supabase
SUPABASE_PUBLIC_BUCKET=false
DATABASE_URL=postgresql://etc..
PARKING_RATE_PER_HOUR=5.0
AUTO_CREATE_SESSION_FROM_OCR=true  # cria sessao automaticamente quando o OCR encontra placa
AUTO_CHARGE_ON_EXIT=true       # debita automaticamente ao fechar a sessao
AUTO_CHARGE_METHOD=auto_charge # texto armazenado em parking_payments.method nos debitos automaticos
PARKING_BILLING_MINUTE_STEP=1  # arredonda o tempo para multiplos de X minutos
PARKING_MINIMUM_FEE=0  
```

O schema mínimo está em `tables.txt` e inclui:

- `parking_event_log` / `parking_sessions` / `parking_payments` (herdados do ALPR antigo)
- `parking_web_users` para os logins do site
- `parking_manual_reservations` para reservas dinâmicas

---

## 2. Fluxo operacional

1. **Marcar vagas**  
   ```bash
   python mark_parking_spots.py --source frame.png --output parking_spots.json --label-prefix vaga --start-index 1
   ```
   - Clique nos 4 pontos de cada vaga; o JSON inclui as coordenadas e um `reference_size` usado para escalonar.

2. **Validar visualmente**  
   ```bash
   python visualize_spots_on_video.py --video video.mp4 --spots parking_spots.json --output video_spots.mp4 --codec mp4v
   ```
   - Gera um MP4 com overlays para conferir se os polígonos batem com o vídeo.

3. **Treinar/testar o classificador**  
   - Use os scripts em `treino/` (`train_spot_classifier.py`, etc.) para produzir o `spot_classifier.pth` (CNN simples 64×64).

4. **Executar o monitor**  
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   - O `parking_monitor_loop` roda em thread separada: captura vídeo, corta cada vaga, processa em batch e publica o estado via `/parking` + WebSocket `/ws`.
   - Quando uma vaga **reservada** muda para ocupada, dispara ALPR async (fast-alpr ONNX) e só então grava a matrícula em memória/BD.

5. **Fluxo web**  
   | Página | Descrição |
   | --- | --- |
   | `/` | Landing page simples com links. |
   | `/live` | Vídeo anotado + cartões das vagas com estado completo (probabilidade, placa, flags). Usa WebSocket em tempo real. |
   | `/reservations` | Tela para o usuário final: login/registro (nome + placa), formulário para reservar vagas livres e painel de vagas (sem expor matrículas). |
   | `/login` | Formulário único para registrar ou entrar; cria sessão via cookies. |
   | `/admin` | Requer login; exibe vídeo, todas as vagas com placas/violação, eventos recentes do ALPR e reservas ativas (com ação de cancelamento). |

Cada reserva dura 24h (configurável); são guardadas em `parking_manual_reservations`, e a lista é exposta tanto para os usuários quanto para o admin.

---

## 3. Comandos auxiliares

| Script | Uso |
| --- | --- |
| `mark_parking_spots.py` | Gera `parking_spots.json` a partir de um frame/imagem (com opção de múltiplos polígonos). |
| `visualize_spots_on_video.py` | Sobrepõe as vagas num vídeo para validação rápida. |
| `monitor_parking_yolo.py` | Variante baseada em YOLO (detecta carros e cruza com vagas). |
| `alpr.py` | Teste local do fast-alpr sem rodar o servidor. |

---

## 4. API e endpoints embutidos

### Páginas HTML
| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/` | Landing page. |
| GET | `/live` | Monitor ao vivo com vídeo + estado das vagas. |
| GET | `/reservations` | Painel de reservas (requere login para reservar). |
| GET | `/login` | Formulário de login/registro (sessão via cookies). |
| GET | `/admin` | Painel completo com vídeo, vagas, eventos e reservas (precisa sessão). |

### APIs em JSON / streaming
| Método | Rota | Descrição / Resposta |
| --- | --- | --- |
| GET | `/parking` | JSON com o estado atual de todas as vagas (`{ "P01": {"occupied": true, "prob": 0.91, ...}, ... }`). |
| GET | `/video_feed` | Stream MJPEG com o último frame anotado. |
| GET | `/plate_events` | Lista das últimas matrículas detectadas (`spot`, `plate`, `ocr_conf`, `reserved`, `violation`, timestamp). |
| POST | `/api/entry` | Regista a entrada de um veículo. Body: `{ "plate": "AA-00-BB", "camera_id": "gate-entrada" }`. Cria/abre um `parking_sessions` com `status=open` e `entry_time=now()`. |
| POST | `/api/exit` | Fecha a sessão de estacionamento: `{ "plate": "AA-00-BB", "camera_id": "gate-saida" }`. Calcula `amount_due` (diferença entre `entry_time` e `now()` multiplicada pela tarifa configurada) e devolve `{ "session_id": ..., "amount_due": 4.50 }`. |
| POST | `/api/payments` | Confirma o pagamento de uma sessão: `{ "session_id": 123, "amount": 4.50, "method": "card" }`. Atualiza `parking_payments` e marca o `parking_sessions.status = 'paid'` ou `amount_paid += amount`. |
| WS | `/ws` | WebSocket que envia o mesmo objeto do `/parking` a cada atualização; usado pelas páginas live/reservas/admin. |
| GET | `/api/reservations` | Lista reservas ativas (`spot`, `plate`, `expires_at`). Sempre sincronizada com o banco. |
| POST | `/api/reservations` | Cria uma reserva para o usuário logado (body: `{ "spot": "P01" }`). Valida se a vaga existe, está livre e não há reserva ativa. |
| DELETE | `/api/reservations/{spot}` | Cancela a reserva da vaga informada. |
| POST | `/api/auth/register` | Regista um novo utilizador com `{ "name": "...", "plate": "AA-00-BB" }`. Responde com nome/placa e abre sessão. |
| POST | `/api/auth/login` | Valida nome + placa e abre sessão. |
| POST | `/api/auth/logout` | Limpa sessão atual. |
| GET | `/api/auth/me` | Retorna os dados do utilizador autenticado ou `401`. |

### Fluxo típico no `/reservations`
1. Usuário acessa `/reservations`; se não estiver logado, atalho para `/login`.
2. `/login` envia `POST /api/auth/register` ou `POST /api/auth/login`. A sessão fica em cookie assinado (`SessionMiddleware`).
3. Ao reservar, a página envia `POST /api/reservations`. O backend verifica vaga livre/ocupada, cria registro no Postgres e atualiza o cache usado pelo WebSocket.
4. Mesmo sem matrícula visível para o usuário comum, o `/admin` recebe tudo (placas, flags de violação, etc.).

---

## 5. Como correr end‑to‑end

1. Defina e teste o classificador + JSON de vagas como descrito na Secção 2.
2. Configure o `.env` com todos os caminhos e o `DATABASE_URL`. Crie as tabelas executando o conteúdo de `tables.txt` no Postgres:
   ```bash
   psql "$DATABASE_URL" -f tables.txt
   ```
3. `uvicorn main:app --reload` e abra:
   - `http://localhost:8000/live` para monitorar
   - `http://localhost:8000/login` / `/reservations` para testar o fluxo do usuário final
   - `http://localhost:8000/admin` para validar que o ALPR está a funcionar e que os eventos aparecem
4. (Opcional) use os scripts listados no topo para gerar os ficheiros auxiliares (`parking_spots.json`, `video_spots.mp4`, etc.).

---

## 6. Extras e troubleshooting

- **fast-alpr ONNX**: por padrão força `CPUExecutionProvider` para evitar erros de TensorRT. Ajuste `ALPR_DETECTOR_PROVIDERS`/`ALPR_OCR_PROVIDERS` se tiver GPU + libs instaladas.
- **Sessões**: `SESSION_SECRET` deve ser longo/aleatório em produção. As sessões expiram após 7 dias (config no middleware).
- **Reservas**: mesmo sem DB, o sistema continua a funcionar com caches em memória, mas serão perdidos ao reiniciar. Defina `DATABASE_URL` para persistir.
- **Logs**: a cada nova detecção de ALPR, um evento é acrescentado ao deque `g_plate_events`; consulte `/plate_events` para debugging rápido.
- **Desempenho**: ajuste `PROCESS_EVERY_N_FRAMES`, `HISTORY_LEN` e o tamanho do batch (`IMG_SIZE`) conforme o hardware e o FPS do vídeo.
