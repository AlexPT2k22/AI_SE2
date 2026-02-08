# AI Smart Parking — Intelligent Parking Management System

A comprehensive, production-ready parking monitoring and management system powered by Artificial Intelligence (Computer Vision) for real-time parking spot detection and Automatic License Plate Recognition (ALPR). The solution integrates IoT hardware (ESP32), a high-performance FastAPI backend, a modern React web dashboard, and a **cross-platform mobile application built with React Native/Expo**.

![Parking Monitor](frame.png)

---

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Backend](#1-backend-setup)
  - [Frontend](#2-web-frontend-setup)
  - [Mobile](#3-mobile-app-setup)
  - [Database](#4-database-setup)
- [Configuration (.env)](#detailed-configuration)
- [Running the System](#running-the-system)
- [API Documentation](#api-documentation)
- [IoT Integration (ESP32)](#iot-integration-esp32)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Features

### Computer Vision & AI
- **Real-Time Spot Detection**: Uses a trained CNN model (ResNet/Custom) to classify parking spots as "Available" or "Occupied" from live video feeds (IP/RTSP cameras or video files).
- **Automatic License Plate Recognition (ALPR)**: Integration with `fast-alpr` (YOLO-based) for automated plate reading at entry and exit gates.
- **Reservation Validation**: Automatically verifies whether a vehicle parked in a reserved spot holds a valid authorization.

### Parking Management
- **Access Control**: Automatic logging of vehicle entries and exits via gate cameras.
- **Session Management**: Automated calculation of parking duration and fees.
- **Reservation System**: Allows users to reserve specific spots for a given time period.
- **Payments**: Supports payment processing via Card, MBWay, or Cash.

### Interfaces
- **Web Dashboard (Frontend)**: A modern React-based interface for real-time visualization of parking lot status.
- **Admin Panel**: Spot management, access log viewing, and financial statistics.
- **WebSocket**: Instant state updates pushed to clients without page refresh.

### Mobile Application
The mobile app provides a full-featured experience for end users:

#### Core Features
- **Login / Registration**: User authentication.
- **Dashboard**: Quick overview of parking statistics (available/occupied spots).
- **Reservations**: Reserve specific spots by zone and time period.
- **History**: View past sessions and payment records.
- **Payments**: Process payments for active parking sessions.

---

## System Architecture

The system consists of four main modules that communicate with each other:

```mermaid
graph TD
    subgraph IoT_Hardware
        ESP32_In[ESP32 Entry Gate] -->|POST Image| API
        ESP32_Out[ESP32 Exit Gate] -->|POST Image| API
        Camera[ESP32 Lot Camera] -->|RTSP Stream| CV_Engine
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

## Technology Stack

### Backend
- **Python 3.13**
- **FastAPI**: High-performance async web framework.
- **Uvicorn**: ASGI server.
- **AsyncPG**: Asynchronous PostgreSQL driver.
- **PyTorch & Torchvision**: Deep Learning model inference.
- **OpenCV**: Image processing pipeline.
- **Fast-ALPR**: License plate detection and OCR.

### Web Frontend
- **React**: UI component library.
- **Vite**: Fast build tool and dev server.
- **TailwindCSS** (via index.css): Utility-first styling.
- **Axios**: HTTP client.

### Mobile
- **React Native**: Cross-platform mobile framework.
- **Expo SDK ~54**: Development platform and toolchain.
- **expo-haptics**: Haptic feedback.
- **expo-linear-gradient**: Gradient support for splash screen.
- **react-native-toast-message**: Toast notifications.
- **@react-native-async-storage/async-storage**: Local data persistence.

### Infrastructure & Data
- **PostgreSQL**: Relational database.
- **Supabase**: Image storage (optional but recommended).
- **Docker** (Optional): Containerization support.

---

## Prerequisites

Before getting started, ensure you have the following installed:
- **Python 3.10+** (3.13 recommended)
- **Node.js 18+** and **npm**
- **PostgreSQL 13+**
- **Git**
- **Expo CLI** (for mobile development): `npm install -g expo-cli`
- **Expo Go** app on your mobile device (iOS/Android) for testing

---

## Installation

### 1. Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AlexPT2k22/AI_SE2.git
    cd AI_SE2
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # Linux/Mac
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you encounter issues with `fast-alpr` or `torch`, refer to the official documentation of those libraries for platform-specific installation instructions (CUDA vs CPU).*

### 2. Web Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install Node dependencies:**
    ```bash
    npm install
    ```

### 3. Mobile App Setup

1.  **Navigate to the mobile directory:**
    ```bash
    cd mobile
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Configure the API URL:**
    In the `App.js` file, update the `API_URL` constant to point to your backend server:
    ```javascript
    const API_URL = 'http://YOUR_IP:8000';
    ```
    *Use your machine's local network IP address (e.g., 192.168.1.100) instead of localhost when testing on physical devices.*

### 4. Database Setup

1.  **Create the database in PostgreSQL:**
    ```sql
    CREATE DATABASE aiparking;
    ```

2.  **Run the table creation script:**
    Use the `tables.txt` file (SQL content) to create the required tables (`parking_sessions`, `parking_payments`, `parking_web_users`, `parking_manual_reservations`).
    ```bash
    psql -d aiparking -f tables.txt
    ```

---

## Detailed Configuration

Create a `.env` file in the project root (`AI_SE2/`) with the following variables:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| **DATABASE** | | |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/aiparking` |
| **SUPABASE (Optional)** | Image storage | |
| `SUPABASE_URL` | Supabase project URL | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | API key (Service Role/Anon) | `eyJ...` |
| `SUPABASE_BUCKET` | Bucket name | `parking-images` |
| `SUPABASE_PUBLIC_BUCKET` | Whether the bucket is public | `false` |
| **GENERAL SETTINGS** | | |
| `VIDEO_SOURCE` | Video file path or RTSP URL | `video.mp4`, `rtsp://...`, or `0` (webcam) |
| `SPOTS_FILE` | JSON file with spot coordinates | `parking_spots.json` |
| `MODEL_FILE` | Trained model file (.pth) | `spot_classifier.pth` |
| `DEVICE` | Inference device | `auto` (uses CUDA if available), `cpu`, `cuda` |
| `SPOT_THRESHOLD` | Minimum confidence for occupancy | `0.7` |
| `PARKING_RATE_PER_HOUR` | Hourly rate (€) | `1.50` |
| `SESSION_SECRET` | Secret key for HTTP sessions | `dev-secret-change-me` |
| **ALPR (License Plates)** | | |
| `ENABLE_ALPR` | Enable plate recognition | `true` |
| `ALPR_WORKERS` | ALPR processing threads | `1` |
| `ALPR_DETECTOR_MODEL` | Detection model | `yolo-v9-s-608-license-plate-end2end` |
| `ALPR_OCR_MODEL` | OCR model | `cct-s-v1-global-model` |

### Parking Spot Configuration (`parking_spots.json`)
This file defines the polygon coordinates for each parking spot. It can be generated using the `mark_parking_spots.py` helper script.

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

## Parking Lot Setup (Required)

> ⚠️ **IMPORTANT**: Before running the system, you must configure the parking spots for your specific lot. The included `parking_spots.json` file is only a sample and **will not work** with your camera or video feed.

### Step 1: Capture a Reference Frame

If using an ESP32-CAM, capture a reference frame:

```bash
# First, update the camera IP address in the script (ESP32_URL)
python capture_esp32_frame.py
```
*This generates the `esp32_reference_frame.jpg` file.*

If using a video file, you can skip this step and use the video directly in the next step.

### Step 2: Mark Parking Spots

Use the interactive tool to draw polygons for each parking spot:

```bash
# From an image (ESP32 capture or screenshot)
python mark_parking_spots.py --source esp32_reference_frame.jpg --output parking_spots.json --show

# From a video file (uses the first frame)
python mark_parking_spots.py --source video.mp4 --output parking_spots.json --show

# From a specific video frame
python mark_parking_spots.py --source video.mp4 --frame 100 --output parking_spots.json --show
```

**Interface Controls:**
| Key | Action |
|------------|--------|
| **Left Click** | Add a point (4 points = 1 spot) |
| **Right Click** | Remove the last point |
| **Enter** | Confirm the current spot and move to the next |
| **S** | Save the JSON file |
| **Q / ESC** | Quit |

### Step 3: Verify the Configuration (Optional)

Visualize the spots overlaid on the video to confirm they are correctly positioned:

```bash
python visualize_spots_on_video.py --video video.mp4 --spots parking_spots.json
```

### Step 4: Run the System

Once the spots are configured, start the backend as described in the [Running the System](#running-the-system) section.

---

## Running the System

It is recommended to open three terminal windows:

### Terminal 1: Backend
```bash
# From the project root (with the virtual environment activated)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*The server will start at http://localhost:8000. Swagger API documentation is available at /docs.*

### Terminal 2: Web Frontend
```bash
# From the frontend/ directory
npm run dev
```
*The web application will be available (typically) at http://localhost:5173.*

### Terminal 3: Mobile App
```bash
# From the mobile/ directory
npm start
# or
npx expo start
```
*Scan the QR code with the Expo Go app on your phone, or press `a` to open the Android emulator / `i` for the iOS simulator.*

---

## API Documentation

Key available endpoints:

### Monitoring
- `GET /parking`: Current status of all parking spots (JSON).
- `GET /video_feed`: MJPEG video stream with real-time annotations.
- `WS /ws`: WebSocket for spot state change events.

### Entry & Exit (ESP32 Integration)
- `POST /api/entry`: Registers a vehicle entry. Accepts `camera_id` and `image` (file). Returns `session_id`.
- `POST /api/exit`: Registers a vehicle exit. Accepts `camera_id` and `image` (file). Calculates the amount due.

### Reservations
- `GET /api/reservations`: Lists active reservations.
- `POST /api/reservations`: Creates a new reservation (requires authentication).
- `DELETE /api/reservations/{spot}`: Cancels a reservation.

### Payments
- `POST /api/payments`: Records a payment for a session.
- `GET /api/sessions`: Retrieves session history.

---

## IoT Integration (ESP32)

The system expects IoT devices (gate cameras) to send HTTP POST `multipart/form-data` requests to the entry and exit endpoints.

**Example workflow:**
1. A vehicle approaches the gate.
2. The ESP32 captures an image.
3. The ESP32 sends a POST request to `http://SERVER_IP:8000/api/entry` with the image.
4. The server processes ALPR, creates a session, and returns a success response.
5. The ESP32 opens the barrier.

---

## Debug Tools

### Debug API (Force Spot State)

Endpoints to manually override the state of a parking spot (useful for testing without a camera):

```bash
# Force a spot as AVAILABLE
curl -X POST http://localhost:8000/api/debug/spot -H "Content-Type: application/json" -d "{\"spot\": \"spot01\", \"occupied\": false}"

# Force a spot as OCCUPIED
curl -X POST http://localhost:8000/api/debug/spot -H "Content-Type: application/json" -d "{\"spot\": \"spot01\", \"occupied\": true}"

# Reset a spot to automatic AI detection
curl -X DELETE http://localhost:8000/api/debug/spot/spot01
```

**Responses:**
```json
// POST - Success
{"message": "Spot spot01 set as available", "spot": "spot01", "occupied": false}

// DELETE - Success
{"message": "Spot spot01 reset to automatic detection"}
```

### Advanced Spot Marker Options

```bash
# Customize spot label prefix and starting index
python mark_parking_spots.py --source frame.jpg --output parking_spots.json --label-prefix "spot" --start-index 1
# Result: spot01, spot02, spot03...

# Export annotated video (without preview window)
python visualize_spots_on_video.py --video video.mp4 --spots parking_spots.json --output runs/video_annotated.mp4 --no-preview
```

---

## Project Structure

```
AI_SE2/
├── frontend/               # React/Vite web frontend source code
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Application pages
│   │   └── styles/         # CSS stylesheets
│   ├── package.json
│   └── vite.config.js
├── mobile/                 # React Native/Expo mobile app source code
│   ├── App.js              # Main application (single-file)
│   ├── package.json
│   └── app.json            # Expo configuration
├── esp32_firmware/         # Arduino code for ESP32 devices
│   ├── center_camera/      # Lot monitoring camera
│   └── entry_gate/         # Entry/exit gate cameras
├── main.py                 # Main application (FastAPI)
├── alpr.py                 # ALPR wrapper module
├── spot_classifier.py      # PyTorch CNN model definition
├── supabaseStorage.py      # Supabase upload service
├── requirements.txt        # Python dependencies
├── parking_spots.json      # Parking spot configuration
├── tables.txt              # Database schema
├── .env                    # Environment variables
└── ...
```

---

## Troubleshooting

### Backend
- **`ImportError: fast_alpr`**: Ensure `fast-alpr` is installed correctly. On Windows, additional steps or WSL2 may be required if the compiled C++ libraries are not available.
- **Database connection error**: Verify that the PostgreSQL service is running and that the `DATABASE_URL` in your `.env` file is correct.
- **Video not opening**: Check the `VIDEO_SOURCE` path. For webcam, try index `0` or `1`. For files, ensure the path is absolute or relative to the project root.

### Web Frontend
- **Frontend cannot connect to backend**: Ensure the frontend is configured to point to `localhost:8000` (via the proxy in `vite.config.js` or a VITE environment variable).

### Mobile
- **App cannot connect to backend**: Use your machine's local network IP (e.g., `192.168.1.100`) instead of `localhost`. Ensure both your phone and computer are on the same Wi-Fi network.
- **Expo Go not loading**: Make sure your firewall is not blocking the Expo ports (19000, 19001, 8081).
- **Haptics not working**: Haptic feedback only works on physical devices, not on emulators or simulators.
