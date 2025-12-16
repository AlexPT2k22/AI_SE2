"""
Script para capturar um frame da ESP32-CAM e guardar como imagem.
Usa esta imagem depois no mark_parking_spots.py para desenhar as zonas.
"""
import cv2
import sys
import numpy as np
import requests

# URL da ESP32-CAM (camara central do estacionamento)
ESP32_BASE = "10.114.226.15"
CAPTURE_URL = f"{ESP32_BASE}/capture"

print(f"A tentar conectar à ESP32-CAM: {CAPTURE_URL}")

try:
    # Usar requests para capturar imagem via /capture (mais fiável)
    response = requests.get(CAPTURE_URL, timeout=30)
    response.raise_for_status()
    
    # Converter para imagem OpenCV
    img_array = np.frombuffer(response.content, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    if frame is None:
        print("Erro: Imagem recebida mas nao consegui descodificar!")
        sys.exit(1)
    
    output_file = "esp32_reference_frame.jpg"
    cv2.imwrite(output_file, frame)
    print(f"Frame capturado e guardado em: {output_file}")
    print(f"  Tamanho: {frame.shape[1]}x{frame.shape[0]} pixels")
    print()
    print("Proximo passo:")
    print(f"  python mark_parking_spots.py --source {output_file} --output parking_spots.json")

except requests.exceptions.Timeout:
    print("Erro: Timeout ao conectar a ESP32-CAM!")
    print("Verifica se:")
    print("  1. A ESP32-CAM esta ligada")
    print("  2. O IP esta correto (10.254.177.15)")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"Erro: {e}")
    print("Verifica se consegues abrir http://10.254.177.15 no browser")
    sys.exit(1)
