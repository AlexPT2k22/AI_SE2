# 🚗 Sistema Inteligente de Gestão de Estacionamento

Sistema completo de monitorização e gestão de estacionamento com detecção automática de vagas, reconhecimento de matrículas (ALPR) e gestão de pagamentos. Desenvolvido com FastAPI, Computer Vision e IoT (ESP32).

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Instalação](#-instalação)
- [Configuração](#%EF%B8%8F-configuração)
- [Execução](#-execução)
- [API Endpoints](#-api-endpoints)
- [Integração ESP32](#-integração-esp32)
- [Base de Dados](#%EF%B8%8F-base-de-dados)
- [Interface Web](#-interface-web)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Funcionalidades

### 🎯 Monitorização de Vagas
- **Detecção automática** de ocupação de vagas via CNN (Convolutional Neural Network)
- **Processamento de vídeo** em tempo real (suporta ficheiros, webcam e RTSP)
- **WebSocket** para atualizações em tempo real
- **Anotação visual** das vagas no stream de vídeo

### 🔍 Reconhecimento de Matrículas (ALPR)
- **Detecção automática** de matrículas usando fast-alpr
- **OCR de alta precisão** para leitura de matrículas portuguesas
- **Processamento em background** para não bloquear detecção de vagas
- **Validação de matrículas** autorizadas em vagas reservadas

### 🎫 Sistema de Reservas
- **Reservas manuais** de vagas por utilizadores
- **Validação automática** de matrículas em vagas reservadas
- **Deteção de violações** (veículo não autorizado em vaga reservada)
- **Expiração automática** de reservas

### 💳 Gestão de Sessões e Pagamentos
- **Registo automático** de entrada/saída via ESP32
- **Cálculo automático** de valores com base no tempo de permanência
- **Sistema de pagamentos** com múltiplos métodos (cartão, dinheiro, MBWay)
- **Histórico completo** de sessões e transações

### 🌐 Interface Web
- **Dashboard em tempo real** com estado das vagas
- **Sistema de autenticação** por nome + matrícula
- **Gestão de reservas** pelos utilizadores
- **Painel administrativo** com estatísticas

---

## 🛠 Tecnologias Utilizadas

### Backend
- **FastAPI** - Framework web assíncrono de alta performance
- **Python 3.13** - Linguagem de programação
- **asyncpg** - Driver PostgreSQL assíncrono
- **python-dotenv** - Gestão de variáveis de ambiente

### Computer Vision & AI
- **PyTorch** - Framework de Deep Learning
- **OpenCV (cv2)** - Processamento de imagem e vídeo
- **fast-alpr** - Reconhecimento de matrículas
- **torchvision** - Transformações de imagem
- **PIL (Pillow)** - Manipulação de imagens

### Base de Dados
- **PostgreSQL** - Base de dados relacional
- **Supabase** (opcional) - Backend-as-a-Service com PostgreSQL

### Hardware & IoT
- **ESP32** - Microcontrolador para captura de matrículas
- **Câmeras IP** (RTSP) - Monitorização do parque

---

## 🏗 Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Server                        │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  Video Thread │  │ ALPR Thread  │  │  WebSocket WSS   │ │
│  │  (CNN Model)  │  │ (fast-alpr)  │  │  (Real-time)     │ │
│  └───────────────┘  └──────────────┘  └──────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           REST API Endpoints (/api/*)                  │ │
│  │  - Entry/Exit (ESP32 image upload)                     │ │
│  │  - Payments                                             │ │
│  │  - Reservations                                         │ │
│  │  - Authentication                                       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓↑
                    PostgreSQL DB
                           ↓↑
              ┌────────────┴────────────┐
              ↓                         ↓
        ESP32 Câmeras              Web Interface
       (Entry/Exit Gates)         (Dashboard/Admin)
```

---

## 📦 Instalação

### Pré-requisitos
- Python 3.13 ou superior
- PostgreSQL 12 ou superior
- Git

### 1. Clonar o Repositório
```bash
git clone <url-do-repositorio>
cd AI_SE2
```

### 2. Criar Ambiente Virtual
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar Base de Dados
```bash
# Criar base de dados PostgreSQL
createdb aiparking

# Executar script SQL para criar tabelas
psql -d aiparking -f tables.txt
```

---

## ⚙️ Configuração

### 1. Arquivo `.env`
Crie um arquivo `.env` na raiz do projeto:

```env
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_BUCKET=nome do bucket
SUPABASE_PUBLIC_BUCKET=false
DATABASE_URL=postgresql://...
PARKING_RATE_PER_HOUR=5.0
AUTO_CREATE_SESSION_FROM_OCR=true  
AUTO_CHARGE_ON_EXIT=true       
AUTO_CHARGE_METHOD=auto_charge 
PARKING_BILLING_MINUTE_STEP=1  
PARKING_MINIMUM_FEE=0  
```

### 2. Configurar Vagas
Edite o arquivo `parking_spots.json` com as coordenadas das vagas ou use o py do mark_parking_spot.py:

```json
{
  "reference_size": [1920, 1080],
  "spots": [
    {
      "name": "A1",
      "points": [[100, 200], [300, 200], [300, 400], [100, 400]],
      "reserved": false,
      "authorized": []
    },
    {
      "name": "B1",
      "points": [[350, 200], [550, 200], [550, 400], [350, 400]],
      "reserved": true,
      "authorized": ["AA-00-BB", "CD-12-EF"]
    }
  ]
}
```

---

## 🚀 Execução

### Iniciar o Servidor
```bash
# Em desenvolvimento (com reload automático)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Em produção
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Acessar Interfaces
- **Swagger UI**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/
- **Live Monitor**: http://localhost:8000/live
- **Reservas**: http://localhost:8000/reservations
- **Admin**: http://localhost:8000/admin

---

## 📡 API Endpoints

### Monitorização

#### `GET /parking`
Retorna estado atual de todas as vagas.

**Resposta:**
```json
{
  "A1": {
    "occupied": true,
    "prob": 0.95,
    "reserved": false,
    "plate": "AA-12-BB",
    "violation": false
  },
  "A2": {
    "occupied": false,
    "prob": 0.12,
    "reserved": false
  }
}
```

#### `GET /video_feed`
Stream MJPEG do vídeo anotado.

#### `GET /plate_events`
Últimas matrículas detectadas.

#### `WS /ws`
WebSocket para atualizações em tempo real.

---

### Entrada/Saída (ESP32)

#### `POST /api/entry`
Registra entrada de veículo com foto da matrícula.

**Requisição:**
```
Content-Type: multipart/form-data

camera_id: "gate-entrada"
image: <arquivo JPEG>
```

**Resposta:**
```json
{
  "session_id": 123,
  "entry_time": "2025-11-26T20:30:15.123456+00:00",
  "plate": "AA-12-BB",
  "camera_id": "gate-entrada"
}

```

#### `POST /api/exit`
Registra saída de veículo e calcula valor devido.

**Requisição:**
```
Content-Type: multipart/form-data

camera_id: "gate-saida"
image: <arquivo JPEG>
```

**Resposta:**
```json
{
  "session_id": 123,
  "plate": "AA-12-BB",
  "entry_time": "2025-11-26T20:30:15+00:00",
  "exit_time": "2025-11-26T21:15:30+00:00",
  "amount_due": 0.68,
  "camera_id": "gate-saida"
}
```

---

### Pagamentos

#### `POST /api/payments`
Registra pagamento de uma sessão.

**Requisição:**
```json
{
  "session_id": 123,
  "amount": 0.68,
  "method": "card"
}
```

**Métodos aceitos:** `card`, `cash`, `mbway`

**Resposta:**
```json
{
  "session_id": 123,
  "amount_paid": 0.68,
  "amount_due": 0.68,
  "status": "paid",
  "payment_method": "card",
  "payment_amount": 0.68
}
```

---

### Reservas

#### `GET /api/reservations`
Lista todas as reservas ativas.

#### `POST /api/reservations`
Cria uma nova reserva (requer autenticação).

**Requisição:**
```json
{
  "spot": "A1",
  "hours": 2
}
```

#### `DELETE /api/reservations/{spot}`
Cancela uma reserva.

---

### Autenticação

#### `POST /api/auth/register`
Regista novo utilizador.

**Requisição:**
```json
{
  "name": "João Silva",
  "plate": "AA-12-BB"
}
```

#### `POST /api/auth/login`
Autentica utilizador.

#### `POST /api/auth/logout`
Termina sessão.

#### `GET /api/auth/me`
Retorna dados do utilizador autenticado.

---

## 📱 Integração ESP32

### Hardware Necessário
- ESP32-CAM ou ESP32 + Módulo de Câmera
- Sensor de proximidade (opcional)
- LED de status

### Exemplo de Código (Arduino)
```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

const char* ssid = "SEU_WIFI";
const char* password = "SUA_SENHA";
const char* serverUrl = "http://192.168.1.100:8000/api/entry";
const char* cameraId = "gate-entrada";

void setup() {
  // Inicializar câmera
  camera_config_t config;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  
  esp_camera_init(&config);
  
  // Conectar WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void sendPlateImage() {
  camera_fb_t* fb = esp_camera_fb_get();
  
  if (!fb) return;
  
  HTTPClient http;
  http.begin(serverUrl);
  
  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  String contentType = "multipart/form-data; boundary=" + boundary;
  
  String body = "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"camera_id\"\r\n\r\n";
  body += cameraId;
  body += "\r\n--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"image\"; filename=\"plate.jpg\"\r\n";
  body += "Content-Type: image/jpeg\r\n\r\n";
  
  uint8_t* buffer = (uint8_t*)malloc(body.length() + fb->len + 100);
  memcpy(buffer, body.c_str(), body.length());
  memcpy(buffer + body.length(), fb->buf, fb->len);
  
  String footer = "\r\n--" + boundary + "--\r\n";
  memcpy(buffer + body.length() + fb->len, footer.c_str(), footer.length());
  
  http.addHeader("Content-Type", contentType);
  int httpCode = http.POST(buffer, body.length() + fb->len + footer.length());
  
  if (httpCode == 200) {
    String response = http.getString();
    // Processar resposta
  }
  
  free(buffer);
  esp_camera_fb_return(fb);
  http.end();
}
```

**Ver documentação completa:** [ESP32_API_GUIDE.md](ESP32_API_GUIDE.md)

---

## 🗄️ Base de Dados

### Tabelas Principais

#### `parking_sessions`
Regista todas as sessões de estacionamento.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | SERIAL | ID único da sessão |
| plate | VARCHAR(32) | Matrícula do veículo |
| camera_id | VARCHAR(64) | ID da câmera de entrada |
| entry_time | TIMESTAMPTZ | Hora de entrada |
| exit_time | TIMESTAMPTZ | Hora de saída |
| amount_due | DECIMAL | Valor a pagar |
| amount_paid | DECIMAL | Valor pago |
| status | VARCHAR(32) | Estado (open/paid/cancelled) |

#### `parking_payments`
Regista todos os pagamentos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | SERIAL | ID único do pagamento |
| session_id | INT | Referência à sessão |
| amount | DECIMAL | Valor pago |
| method | VARCHAR(32) | Método de pagamento |
| created_at | TIMESTAMPTZ | Data do pagamento |

#### `parking_web_users`
Utilizadores registados na plataforma web.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| full_name | VARCHAR(80) | Nome completo |
| plate | VARCHAR(32) | Matrícula (PK) |
| plate_norm | VARCHAR(32) | Matrícula normalizada |

#### `parking_manual_reservations`
Reservas manuais de vagas.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| spot | VARCHAR(32) | Nome da vaga (PK) |
| plate | VARCHAR(32) | Matrícula |
| reserved_by | VARCHAR(80) | Nome do reservante |
| reserved_until | TIMESTAMPTZ | Validade da reserva |

---

## 🖥 Interface Web

### Dashboard Principal
- Visualização em tempo real do estado das vagas
- Mapa visual do parque de estacionamento
- Estatísticas de ocupação

### Gestão de Reservas
- Login seguro com nome + matrícula
- Reserva de vagas disponíveis
- Visualização das suas reservas ativas
- Cancelamento de reservas

### Painel Admin
- Stream de vídeo anotado em tempo real
- Lista de todas as vagas com estado
- Histórico de detecções de matrículas
- Gestão de reservas

---

## 🔧 Troubleshooting

### Problema: "DATABASE_URL não configurada"
**Solução:** Certifique-se de que o arquivo `.env` existe e contém `DATABASE_URL=postgresql://...`

### Problema: "Base de dados indisponível" (503)
**Soluções:**
1. Verifique se o PostgreSQL está a correr
2. Teste a conexão: `python test_db_connection.py`
3. Verifique as credenciais no `.env`

### Problema: ALPR não detecta matrículas
**Soluções:**
1. Certifique-se de que a imagem está bem iluminada
2. A matrícula deve estar em foco
3. Aumente a resolução da imagem (mínimo 640x480)
4. Verifique se `ENABLE_ALPR=true` no `.env`

### Problema: CNN não deteta ocupação correta
**Soluções:**
1. Ajuste `SPOT_THRESHOLD` no `.env` (padrão: 0.7)
2. Retreine o modelo com mais exemplos
3. Verifique se as coordenadas em `parking_spots.json` estão corretas

### Problema: Vídeo não abre
**Soluções:**
1. Verifique o caminho em `VIDEO_SOURCE`
2. Para RTSP, teste: `ffplay rtsp://camera-ip:554/stream`
3. Para webcam, tente `VIDEO_SOURCE=0`

---
