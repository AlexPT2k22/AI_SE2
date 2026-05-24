<div align="center">
  <h1>TugaPark — AI Smart Parking</h1>
  <p><strong>Intelligent Parking Management System</strong> powered by Computer Vision, IoT, and Machine Learning</p>

  <br/>

  <p>
    <a href="[https://tugapark.vercel.app](https://ai-se-2.vercel.app/)" target="_blank">
      <img src="https://img.shields.io/badge/LIVE_DEMO-Vercel-000?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Demo"/>
    </a>
    &nbsp;
    <a href="https://github.com/AlexPT2k22/AI_SE2/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="License"/>
    </a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
    <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=white" alt="React"/>
    <img src="https://img.shields.io/badge/React_Native-Expo-000020?style=flat-square&logo=expo&logoColor=white" alt="Expo"/>
    <img src="https://img.shields.io/badge/PyTorch-2.5-EE4C2C?style=flat-square&logo=pytorch&logoColor=white" alt="PyTorch"/>
    <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
    <img src="https://img.shields.io/badge/ESP32_CAM-IoT-E7352C?style=flat-square&logo=espressif&logoColor=white" alt="ESP32"/>
    <img src="https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite&logoColor=white" alt="Vite"/>
  </p>

  <br/>
</div>

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🎮 Live Demo](#-live-demo)
- [🏗️ Architecture](#️-architecture)
- [🛠️ Tech Stack](#️-tech-stack)
- [📸 Screenshots](#-screenshots)
- [🚀 Quick Start](#-quick-start)
- [📖 API Documentation](#-api-documentation)
- [🔧 Parking Lot Setup](#-parking-lot-setup)
- [📱 Mobile App](#-mobile-app)
- [🔌 IoT Integration (ESP32)](#-iot-integration-esp32)
- [🤖 ML Model Training](#-ml-model-training)
- [📁 Project Structure](#-project-structure)
- [🌐 Deployment](#-deployment)

---

## ✨ Features

### 🧠 Computer Vision & AI

| Feature | Description |
|---|---|
| **Real-Time Detection** | CNN-based parking spot classification (available/occupied) from live video |
| **License Plate Recognition** | YOLO-based ALPR for automatic plate reading at entry/exit gates |
| **Reservation Validation** | Detects unauthorized vehicles parked in reserved spots |
| **Temporal Smoothing** | Sliding window filter prevents false state changes |
| **Batch Inference** | All spots processed simultaneously via PyTorch |

### 🅿️ Parking Management

- **Access Control** — Automatic vehicle entry/exit logging via ESP32 gate cameras
- **Session Management** — Automated duration calculation and fee computation (€1.50/h)
- **Reservation System** — Reserve spots for today or tomorrow with fine enforcement (€20 no-show)
- **Payments** — Card (auto-pay), MB Way, and Cash support
- **Admin Dashboard** — Real-time stats, violation alerts, revenue tracking

### 📱 Multi-Platform

| Platform | Stack | Features |
|---|---|---|
| **Web Dashboard** | React + Vite + TailwindCSS | Real-time WebSocket updates, spot visualization, admin panel |
| **Mobile App** | React Native + Expo SDK 54 | Reservations, payments, vehicles, notifications, biometric auth |
| **IoT Hardware** | ESP32-CAM (Arduino) | Entry/exit gate automation, MJPEG lot streaming |

---

## 🎮 Live Demo

> **Try the web dashboard live on Vercel — no installation required!**

<p align="center">
  <a href="https://tugapark.vercel.app" target="_blank">
    <img src="https://img.shields.io/badge/🌐_LAUNCH_LIVE_DEMO-18181B?style=for-the-badge&logo=vercel&logoColor=white" alt="Launch Demo"/>
  </a>
</p>

The demo runs in **mock mode** with simulated data:
- ✅ Full UI experience (Home, Live Monitor, Reservations, Profile, Admin)
- 🔄 Real-time spot state changes (WebSocket simulation)
- 🚗 Mock vehicles, reservations, and payment methods
- 👤 Demo credentials: `demo@tugapark.com` / any password
- 🔑 Admin access: all features unlocked

<details>
<summary><b>📱 Mobile App Preview</b></summary>
<br/>
The mobile app is not deployed online, but you can run it locally:
<pre><code>cd mobile
npm install
npx expo start
</code></pre>
Scan the QR code with Expo Go on your phone.
</details>

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "🌐 Clients"
        Web["React Web App<br/>(Vite + TailwindCSS)"]
        Mobile["React Native App<br/>(Expo SDK 54)"]
    end

    subgraph "⚡ Backend Server"
        API["FastAPI Server<br/>Uvicorn + asyncpg"]
        CV["Computer Vision Engine<br/>PyTorch + OpenCV"]
        WS["WebSocket Manager"]
        
        CV -->|state updates| WS
        API -->|CRUD| DB[("PostgreSQL<br/>Supabase")]
        API -->|upload| Storage["Supabase Storage<br/>(entry/exit images)"]
    end

    subgraph "🤖 IoT Hardware"
        ESP32_In["ESP32 Entry Gate<br/>Ultrasonic + Servo"]
        ESP32_Out["ESP32 Exit Gate"]
        Camera["ESP32 Lot Camera<br/>MJPEG Stream"]
    end

    subgraph "🧠 ML Pipeline"
        Inference["Spot Classifier<br/>CNN (PyTorch)"]
        ALPR["Fast-ALPR<br/>YOLO + OCR"]
        Training["Training Pipeline<br/>Data collection + Augmentation"]
    end

    Web -->|HTTP REST| API
    Web -->|WebSocket| WS
    Web -->|MJPEG| CV
    Mobile -->|HTTP REST| API

    ESP32_In -->|POST /api/entry| API
    ESP32_Out -->|POST /api/exit| API
    Camera -->|RTSP/HTTP Stream| CV

    CV -->|batch inference| Inference
    CV -->|state change| ALPR
```

### Data Flow

1. **Parking Lot Camera** streams MJPEG to the backend
2. **CV Engine** extracts 64×64 crops for each defined parking spot polygon
3. **CNN Model** classifies each crop as available/occupied (batch inference)
4. **Temporal smoothing** filters false positives across N frames
5. **State change** (free→occupied) triggers ALPR for license plate detection
6. **WebSocket** broadcasts updated state to all connected clients
7. **Entry/Exit Gates** send photos via HTTP POST; ALPR reads plates automatically
8. **Database** records sessions, payments, reservations, and notifications

---

## 🛠️ Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| **Python 3.13** | Core language |
| **FastAPI** | Async web framework with auto-generated OpenAPI docs |
| **Uvicorn** | ASGI server |
| **AsyncPG** | Async PostgreSQL driver |
| **PyTorch 2.5** | CNN model inference |
| **OpenCV** | Image processing, frame capture, annotation |
| **Fast-ALPR** | YOLO-based license plate detection + OCR |

### Web Frontend

| Technology | Purpose |
|---|---|
| **React 18** | UI components |
| **Vite 5** | Build tool and dev server |
| **React Router v6** | Client-side routing |
| **Axios** | HTTP client with JWT support |
| **CSS Variables** | Theming (dark mode ready) |

### Mobile

| Technology | Purpose |
|---|---|
| **React Native** | Cross-platform framework |
| **Expo SDK ~54** | Development toolchain |
| **AsyncStorage** | JWT persistence |
| **expo-haptics** | Haptic feedback |
| **react-native-toast-message** | Toast notifications |

### Infrastructure

| Technology | Purpose |
|---|---|
| **PostgreSQL 16** | Relational database |
| **Supabase** | Image storage (optional) |
| **Vercel** | Frontend hosting (live demo) |

---

## 📸 Screenshots

<div align="center">
  <table>
    <tr>
      <td align="center"><strong>📊 Live Monitor</strong></td>
    </tr>
    <tr>
      <td>
        <img src="output_overlay-ezgif.com-optimize.gif" alt="Live Monitor" width="400"/>
      </td>
    </tr>
    <tr>
      <td align="center"><strong>Training Accuracy</strong></td>
      <td align="center"><strong>Training Loss</strong></td>
    </tr>
    <tr>
      <td>
        <img src="training_accuracy.png" alt="Training Accuracy" width="400"/>
      </td>
      <td>
        <img src="training_loss.png" alt="Training Loss" width="400"/>
      </td>
    </tr>
  </table>
</div>

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+, Node.js 18+, PostgreSQL 16+
- ESP32-CAM hardware (optional — video files work too)

### 1. Backend

```bash
# Clone & enter
git clone https://github.com/AlexPT2k22/AI_SE2.git
cd AI_SE2

# Virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# Install
pip install -r requirements.txt

# Configure .env (see Configuration section)
# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Web Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173

# For standalone demo (mock mode, no backend needed):
npm run dev:mock     # or: VITE_MOCK=true npm run dev
```

### 3. Mobile App

```bash
cd mobile
npm install
npx expo start
```

### 4. Database

```sql
CREATE DATABASE aiparking;
psql -d aiparking -f tables.txt
```

### Configuration

Create `.env` in project root:

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/aiparking
VIDEO_SOURCE=video.mp4          # or 0 (webcam) or RTSP URL
SPOTS_FILE=parking_spots.json
MODEL_FILE=spot_classifier.pth
PARKING_RATE_PER_HOUR=1.50
ENABLE_ALPR=true
```

---

## 📖 API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/parking` | Current status of all parking spots |
| `GET` | `/video_feed` | Annotated MJPEG video stream |
| `WS` | `/ws` | WebSocket for real-time updates |
| `POST` | `/api/entry` | Register vehicle entry (ESP32) |
| `POST` | `/api/exit` | Register vehicle exit (ESP32) |
| `GET` | `/api/reservations` | List active reservations |
| `POST` | `/api/reservations` | Create reservation |
| `POST` | `/api/payments` | Process payment |
| `POST` | `/api/auth/login` | User login (email or plate) |
| `GET` | `/api/admin/stats` | Admin statistics |

> Full interactive docs at `http://localhost:8000/docs` (Swagger UI)

---

## 🔧 Parking Lot Setup

```bash
# Step 1: Capture reference frame
python capture_esp32_frame.py

# Step 2: Mark spots (interactive)
python mark_parking_spots.py --source esp32_reference_frame.jpg --output parking_spots.json --show

# Controls: Left Click = add point | Enter = confirm spot | S = save | Q = quit

# Step 3: Verify alignment
python visualize_spots_on_video.py --video video.mp4 --spots parking_spots.json
```

---

## 📱 Mobile App

The React Native app provides:
- **Dashboard** with real-time parking stats
- **Reservations** (today/tomorrow with fine enforcement)
- **Session history** and payment records
- **Vehicle & card management**
- **Biometric authentication** (fingerprint/Face ID)
- **Dark/light theme**
- **Haptic feedback** on interactions

---

## 🔌 IoT Integration (ESP32)

### Entry Gate (`esp32_firmware/entry_gate/`)
- HC-SR04 ultrasonic sensor detects approaching vehicles
- Captures photo and sends to `POST /api/entry`
- Opens barrier via servo motor
- Red/green LED status indicators

### Exit Gate
- Captures photo and sends to `POST /api/exit`
- Validates payment before opening barrier

### Lot Camera (`esp32_firmware/center_camera/`)
- Continuous MJPEG stream for the CV pipeline
- HTTP endpoints: `/stream`, `/capture`, `/`

---

## 🤖 ML Model Training

```bash
# 1. Collect training data
python collect_training_data.py

# 2. Train the CNN
python train_parking_model.py

# 3. Monitor with trained model
python main.py
```

**Model Architecture**: 3× Conv2D (16→32→64 filters) → 2× FC (128→2)
**Input**: 64×64 RGB crops
**Augmentation**: flips, rotation, color jitter, affine transforms
**Regularization**: dropout, weight decay

---

## 📁 Project Structure

```
AI_SE2/
├── frontend/                    # React/Vite web app
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Application pages
│   │   ├── mock/                # Mock data for standalone demo
│   │   ├── contexts/            # Auth context
│   │   └── api.js               # API client (JWT + mock support)
│   ├── public/                  # Static assets
│   ├── vercel.json              # Vercel deployment config
│   └── vite.config.js
├── mobile/                      # React Native/Expo app
│   └── App.js                   # Main application (single-file)
├── esp32_firmware/              # Arduino code
│   ├── center_camera/           # Lot monitoring camera
│   └── entry_gate/              # Entry/exit gate cameras
├── main.py                      # FastAPI server (CV + WS + REST)
├── spot_classifier.py           # PyTorch CNN model
├── alpr.py                      # License plate recognition
├── auth_module.py               # Auth v2.0 (JWT + bcrypt)
├── auth_routes.py               # Auth API endpoints
├── supabaseStorage.py           # Supabase upload service
├── mark_parking_spots.py        # Interactive spot marker
├── train_parking_model.py       # Model training pipeline
├── parking_spots.json           # Spot polygon config
├── tables.txt                   # Database schema
└── requirements.txt
```

---

## 🌐 Deployment

### Frontend (Vercel)

The web app is configured for one-click deploy:

[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FAlexPT2k22%2FAI_SE2&project-name=tugapark&repository-name=AI_SE2&root-directory=frontend&env=VITE_MOCK&envValue=true)

The deploy runs in **mock mode** — no backend required. For a full deployment, set up the backend on [Railway](https://railway.app) or [Render](https://render.com).

### Backend (Railway/Render)

```bash
# Deploy FastAPI
railway up
# or
render deploy
```

Requires: PostgreSQL instance, `DATABASE_URL` env var, `parking_spots.json`.

---

<div align="center">
  <br/>
  <p>
    <strong>TugaPark</strong> — Built with ❤️ by
    <a href="https://github.com/AlexPT2k22">AlexPT2k22</a>
  </p>
  <p>
    <a href="https://github.com/AlexPT2k22/AI_SE2/issues">Report Bug</a>
    ·
    <a href="https://github.com/AlexPT2k22/AI_SE2/discussions">Request Feature</a>
  </p>
  <br/>
</div>
