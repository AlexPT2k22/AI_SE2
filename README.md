# Sistema Inteligente de Gestão de Estacionamento (AI Smart Parking)

Sistema completo e moderno de monitorização e gestão de estacionamento que utiliza Inteligência Artificial (Computer Vision) para detecção de vagas em tempo real e reconhecimento de matrículas (ALPR). A solução integra hardware IoT (ESP32), um backend robusto em FastAPI, uma interface frontend moderna em React e uma **aplicação mobile em React Native/Expo**.

![Parking Monitor](frame.png)

---

## Índice

- [Funcionalidades](#-funcionalidades)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
  - [Backend](#1-configuração-do-backend)
  - [Frontend](#2-configuração-do-frontend)
  - [Mobile](#3-configuração-do-mobile)
  - [Base de Dados](#4-configuração-da-base-de-dados)
- [Configuração (.env)](#%EF%B8%8F-configuração-detalhada)
- [Execução](#-execução)
- [API Endpoints](#-documentação-da-api)
- [Integração IoT (ESP32)](#-integração-iot-esp32)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Troubleshooting](#-troubleshooting)

---

## Funcionalidades

### Visão Computacional & AI
- **Detecção de Vagas em Tempo Real**: Utiliza um modelo CNN (ResNet/Custom) treinado para classificar vagas como "Livre" ou "Ocupada" a partir de feeds de vídeo (Câmeras IP/RTSP ou arquivos).
- **Reconhecimento de Matrículas (ALPR)**: Integração com `fast-alpr` (baseado em YOLO) para leitura automática de matrículas nas entradas e saídas.
- **Validação de Reservas**: Verifica automaticamente se um veículo estacionado numa vaga reservada possui autorização.

### Gestão de Estacionamento
- **Controlo de Acesso**: Registo automático de entradas e saídas via câmeras nos portões.
- **Gestão de Sessões**: Cálculo automático do tempo de permanência e valor a pagar.
- **Sistema de Reservas**: Permite aos utilizadores reservar vagas específicas por um determinado período.
- **Pagamentos**: Simulação de pagamentos via Cartão, MBWay ou Dinheiro.

### Interfaces
- **Dashboard Web (Frontend)**: Interface moderna em React para visualização do estado do parque em tempo real.
- **Painel Administrativo**: Gestão de vagas, visualização de logs de acesso e estatísticas financeiras.
- **WebSocket**: Atualizações instantâneas do estado das vagas sem necessidade de refresh.

### Aplicação Mobile
A aplicação mobile oferece uma experiência completa para utilizadores finais:

#### Funcionalidades Core
- **Login/Registo**: Autenticação de utilizadores.
- **Dashboard**: Visualização rápida de estatísticas (vagas livres/ocupadas).
- **Reservas**: Reservar vagas específicas por zona e período.
- **Histórico**: Consultar sessões anteriores e pagamentos.
- **Pagamentos**: Efetuar pagamentos de sessões ativas.

---

## Arquitetura do Sistema

O sistema é composto por quatro módulos principais que comunicam entre si:

```mermaid
graph TD
    subgraph IoT_Hardware
        ESP32_In[ESP32 Entrada] -->|POST Image| API
        ESP32_Out[ESP32 Saída] -->|POST Image| API
        Camera[ESP32 Vagas] -->|RTSP Stream| CV_Engine
    end

    subgraph Backend_Server
        API[FastAPI Server]
        CV_Engine[Computer Vision Engine]
        WS[WebSocket Manager]

        CV_Engine -->|Update State| WS
        API -->|CRUD| DB[(PostgreSQL)]
        API -->|Upload| Storage[Supabase Storage]
    end

    subgraph Frontend_Client
        Web[React Web App]
        Web -->|HTTP| API
        Web -->|WS| WS
    end

    subgraph Mobile_Client
        Mobile[React Native App]
        Mobile -->|HTTP| API
    end
```

---

## Tecnologias Utilizadas

### Backend
- **Python 3.13**
- **FastAPI**: Framework web de alta performance.
- **Uvicorn**: Servidor ASGI.
- **AsyncPG**: Driver assíncrono para PostgreSQL.
- **PyTorch & Torchvision**: Para execução dos modelos de Deep Learning.
- **OpenCV**: Processamento de imagem.
- **Fast-ALPR**: Detecção e OCR de matrículas.

### Frontend Web
- **React**: Biblioteca JS para interfaces.
- **Vite**: Build tool rápida.
- **TailwindCSS** (via index.css): Estilização.
- **Axios**: Requisições HTTP.

### Mobile
- **React Native**: Framework para apps nativas.
- **Expo SDK ~54**: Plataforma de desenvolvimento.
- **expo-haptics**: Feedback tátil.
- **expo-linear-gradient**: Gradientes para splash screen.
- **react-native-toast-message**: Notificações toast.
- **@react-native-async-storage/async-storage**: Persistência local.

### Infraestrutura & Dados
- **PostgreSQL**: Base de dados relacional.
- **Supabase**: Armazenamento de imagens (opcional, mas recomendado).
- **Docker** (Opcional): Para containerização.

---

## Pré-requisitos

Antes de começar, certifique-se de ter instalado:
- **Python 3.10+** (Recomendado 3.13)
- **Node.js 18+** e **npm**
- **PostgreSQL 13+**
- **Git**
- **Expo CLI** (para desenvolvimento mobile): `npm install -g expo-cli`
- **Expo Go** app no telemóvel (iOS/Android) para testes

---

## Instalação

### 1. Configuração do Backend

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/AI_SE2.git
    cd AI_SE2
    ```

2.  **Crie e ative o ambiente virtual:**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # Linux/Mac
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
    *Nota: Se tiver problemas com o `fast-alpr` ou `torch`, consulte a documentação oficial dessas bibliotecas para instalação específica do seu SO/Hardware (CUDA vs CPU).*

### 2. Configuração do Frontend Web

1.  **Navegue para a pasta do frontend:**
    ```bash
    cd frontend
    ```

2.  **Instale as dependências do Node:**
    ```bash
    npm install
    ```

### 3. Configuração do Mobile

1.  **Navegue para a pasta mobile:**
    ```bash
    cd mobile
    ```

2.  **Instale as dependências:**
    ```bash
    npm install
    ```

3.  **Configure a URL da API:**
    No ficheiro `App.js`, atualize a constante `API_URL` para apontar para o seu servidor backend:
    ```javascript
    const API_URL = 'http://YOUR_IP:8000';
    ```
    *Use o IP da sua máquina na rede local (ex: 192.168.1.100) em vez de localhost para testes em dispositivos físicos.*

### 4. Configuração da Base de Dados

1.  **Crie a base de dados no PostgreSQL:**
    ```sql
    CREATE DATABASE aiparking;
    ```

2.  **Execute o script de criação das tabelas:**
    Você pode usar o arquivo `tables.txt` (conteúdo SQL) para criar as tabelas necessárias (`parking_sessions`, `parking_payments`, `parking_web_users`, `parking_manual_reservations`).
    ```bash
    psql -d aiparking -f tables.txt
    ```

---

## Configuração Detalhada

Crie um arquivo `.env` na raiz do projeto (`AI_SE2/`) com as seguintes variáveis:

| Variável | Descrição | Valor Padrão / Exemplo |
| :--- | :--- | :--- |
| **DATABASE** | | |
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql://user:pass@localhost:5432/aiparking` |
| **SUPABASE (Opcional)** | Armazenamento de imagens | |
| `SUPABASE_URL` | URL do projeto Supabase | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | Chave de API (Service Role/Anon) | `eyJ...` |
| `SUPABASE_BUCKET` | Nome do bucket | `parking-images` |
| `SUPABASE_PUBLIC_BUCKET` | Se o bucket é público | `false` |
| **CONFIGURAÇÃO GERAL** | | |
| `VIDEO_SOURCE` | Caminho do vídeo ou URL RTSP | `video.mp4` ou `rtsp://...` ou `0` (webcam) |
| `SPOTS_FILE` | Arquivo JSON com coordenadas | `parking_spots.json` |
| `MODEL_FILE` | Modelo treinado (.pth) | `spot_classifier.pth` |
| `DEVICE` | Dispositivo de inferência | `auto` (escolhe cuda se disponível), `cpu`, `cuda` |
| `SPOT_THRESHOLD` | Confiança mínima para ocupação | `0.7` |
| `PARKING_RATE_PER_HOUR` | Custo por hora (€) | `1.50` |
| `SESSION_SECRET` | Chave para sessões HTTP | `dev-secret-change-me` |
| **ALPR (Matrículas)** | | |
| `ENABLE_ALPR` | Ativar reconhecimento? | `true` |
| `ALPR_WORKERS` | Threads para ALPR | `1` |
| `ALPR_DETECTOR_MODEL` | Modelo de detecção | `yolo-v9-s-608-license-plate-end2end` |
| `ALPR_OCR_MODEL` | Modelo de OCR | `cct-s-v1-global-model` |

### Configuração das Vagas (`parking_spots.json`)
Este arquivo define as coordenadas dos polígonos de cada vaga. Pode ser gerado usando o script auxiliar `mark_parking_spots.py`.

```json
{
  "reference_size": {"width": 1920, "height": 1080},
  "spots": [
    {
      "name": "A1",
      "points": [{"x": 100, "y": 200}, ...],
      "reserved": false,
      "authorized_plates": []
    }
  ]
}
```

---

## Configuração do Estacionamento (Obrigatório)

> ⚠️ **IMPORTANTE**: Antes de executar o sistema, é necessário configurar as vagas do seu estacionamento. O ficheiro `parking_spots.json` incluído é apenas um exemplo e **não funcionará** com a sua câmara/vídeo.

### Passo 1: Capturar Frame de Referência

Se estiver a usar uma ESP32-CAM, capture um frame para usar como referência:

```bash
# Edita primeiro o IP da câmara no script (ESP32_URL)
python capture_esp32_frame.py
```
*Gera o ficheiro `esp32_reference_frame.jpg`.*

Se estiver a usar um ficheiro de vídeo, pode saltar este passo e usar o vídeo diretamente no passo seguinte.

### Passo 2: Marcar as Vagas

Use a ferramenta interativa para desenhar os polígonos de cada vaga:

```bash
# A partir de uma imagem (ESP32 ou screenshot)
python mark_parking_spots.py --source esp32_reference_frame.jpg --output parking_spots.json --show

# A partir de um vídeo (usa o primeiro frame)
python mark_parking_spots.py --source video.mp4 --output parking_spots.json --show

# A partir de um frame específico do vídeo
python mark_parking_spots.py --source video.mp4 --frame 100 --output parking_spots.json --show
```

**Controlos da Interface:**
| Tecla | Função |
|------------|--------|
| **Click esquerdo** | Adiciona um ponto (4 pontos = 1 vaga) |
| **Click direito** | Remove o último ponto |
| **Enter** | Confirma a vaga atual e passa à próxima |
| **S** | Guarda o ficheiro JSON |
| **Q / ESC** | Sair |

### Passo 3: Verificar a Configuração (Opcional)

Visualize as vagas sobrepostas no vídeo para confirmar que estão corretas:

```bash
python visualize_spots_on_video.py --video video.mp4 --spots parking_spots.json
```

### Passo 4: Executar o Sistema

Depois de configurar as vagas, pode iniciar o backend normalmente (ver secção [Execução](#execução)).

---

## Execução

Recomenda-se abrir três terminais:

### Terminal 1: Backend
```bash
# Na raiz do projeto (com venv ativado)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*O servidor iniciará em http://localhost:8000. A documentação Swagger estará em /docs.*

### Terminal 2: Frontend Web
```bash
# Na pasta frontend/
npm run dev
```
*A aplicação web estará disponível (geralmente) em http://localhost:5173.*

### Terminal 3: Mobile
```bash
# Na pasta mobile/
npm start
# ou
npx expo start
```
*Scan o QR code com a app Expo Go no telemóvel ou pressione `a` para abrir no emulador Android / `i` para iOS. (ou conecte via USB e pressione a tecla)*

---

## Documentação da API

Principais endpoints disponíveis:

### Monitorização
- `GET /parking`: Estado atual de todas as vagas (JSON).
- `GET /video_feed`: Stream MJPEG do vídeo com anotações em tempo real.
- `WS /ws`: WebSocket para eventos de mudança de estado.

### Entrada e Saída (Integração ESP32)
- `POST /api/entry`: Regista entrada. Recebe `camera_id` e `image` (file). Retorna `session_id`.
- `POST /api/exit`: Regista saída. Recebe `camera_id` e `image` (file). Calcula valor a pagar.

### Reservas
- `GET /api/reservations`: Lista reservas ativas.
- `POST /api/reservations`: Cria nova reserva (Requer Auth).
- `DELETE /api/reservations/{spot}`: Cancela reserva.

### Pagamentos
- `POST /api/payments`: Regista pagamento de uma sessão.
- `GET /api/sessions`: Histórico de sessões.

---

## Integração IoT (ESP32)

O sistema espera que os dispositivos IoT (câmeras nos portões) enviem requisições HTTP POST `multipart/form-data` para os endpoints de entrada e saída.

**Exemplo de fluxo:**
1. Carro aproxima-se do portão.
2. ESP32 tira foto.
3. ESP32 envia POST para `http://SERVER_IP:8000/api/entry` com a imagem.
4. Servidor processa ALPR, cria sessão e retorna sucesso.
5. ESP32 abre a cancela.
---

## Ferramentas de Debug

### API de Debug (Forçar Estado de Vagas)

Endpoints para forçar manualmente o estado de uma vaga (útil para testes sem câmara):

```bash
# Forçar vaga como LIVRE
curl -X POST http://localhost:8000/api/debug/spot \
  -H "Content-Type: application/json" \
  -d "{\"spot\": \"spot01\", \"occupied\": false}"

# Forçar vaga como OCUPADA
curl -X POST http://localhost:8000/api/debug/spot \
  -H "Content-Type: application/json" \
  -d "{\"spot\": \"spot01\", \"occupied\": true}"

# Resetar vaga para deteção automática (volta a usar o modelo AI)
curl -X DELETE http://localhost:8000/api/debug/spot/spot01
```

**Respostas:**
```json
// POST - Sucesso
{"message": "Spot spot01 definido como livre", "spot": "spot01", "occupied": false}

// DELETE - Sucesso
{"message": "Spot spot01 resetado para deteção automática"}
```

### Opções Avançadas do Marcador de Vagas

```bash
# Personalizar prefixo e índice inicial dos nomes das vagas
python mark_parking_spots.py --source frame.jpg --output parking_spots.json --label-prefix "A" --start-index 1
# Resultado: A1, A2, A3...

# Exportar vídeo anotado (sem janela de preview)
python visualize_spots_on_video.py --video video.mp4 --spots parking_spots.json --output runs/video_annotated.mp4 --no-preview
```

---

## Estrutura do Projeto

```
AI_SE2/
├── frontend/               # Código fonte React/Vite (Web)
│   ├── src/
│   │   ├── components/     # Componentes reutilizáveis
│   │   ├── pages/          # Páginas da aplicação
│   │   └── styles/         # Estilos CSS
│   ├── package.json
│   └── vite.config.js
├── mobile/                 # Código fonte React Native/Expo
│   ├── App.js              # Aplicação principal (single-file)
│   ├── package.json
│   └── app.json            # Configuração Expo
├── esp32_firmware/         # Código Arduino para ESP32
│   ├── center_camera/      # Câmera central
│   └── entry_gate/         # Portões de entrada/saída
├── main.py                 # Aplicação Principal (FastAPI)
├── alpr.py                 # Módulo wrapper para ALPR
├── spot_classifier.py      # Definição do modelo PyTorch (CNN)
├── supabaseStorage.py      # Serviço de upload para Supabase
├── requirements.txt        # Dependências Python
├── parking_spots.json      # Configuração das vagas
├── tables.txt              # Schema da Base de Dados
├── .env                    # Variáveis de ambiente
└── ...
```

---

## Troubleshooting

### Backend
- **Erro `ImportError: fast_alpr`**: Certifique-se de que instalou o `fast-alpr` corretamente. Em Windows, pode requerer passos adicionais ou uso de WSL2 se as bibliotecas C++ compiladas não estiverem disponíveis.
- **Erro de Conexão DB**: Verifique se o serviço PostgreSQL está rodando e se a `DATABASE_URL` no `.env` está correta.
- **Vídeo não abre**: Verifique o caminho em `VIDEO_SOURCE`. Se usar webcam, tente index `0` ou `1`. Se usar arquivo, garanta que o caminho é absoluto ou relativo à raiz.

### Frontend Web
- **Frontend não conecta ao Backend**: Verifique se o frontend está configurado para apontar para `localhost:8000` (proxy no `vite.config.js` ou variável de ambiente VITE).

### Mobile
- **App não conecta ao Backend**: Use o IP da sua máquina na rede local (ex: `192.168.1.100`) em vez de `localhost`. Verifique se o telemóvel e o computador estão na mesma rede Wi-Fi.
- **Expo Go não carrega**: Certifique-se de que o firewall não está a bloquear as portas do Expo (19000, 19001, 8081).
- **Haptics não funciona**: O feedback háptico só funciona em dispositivos físicos, não em emuladores/simuladores.
