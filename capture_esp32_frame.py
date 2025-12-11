"""
Script para capturar um frame da ESP32-CAM e guardar como imagem.
Usa esta imagem depois no mark_parking_spots.py para desenhar as zonas.
"""
import cv2
import sys

# URL da ESP32-CAM (camara central do estacionamento)
ESP32_URL = "http://10.254.177.248/stream"

print(f"A tentar conectar à ESP32-CAM: {ESP32_URL}")
cap = cv2.VideoCapture(ESP32_URL)

if not cap.isOpened():
    print("Erro: Nao consegui conectar a ESP32-CAM!")
    print("Verifica se:")
    print("  1. A ESP32-CAM esta ligada")
    print("  2. O IP esta correto (10.254.177.248)")
    print("  3. Consegues abrir http://10.254.177.248 no browser")
    sys.exit(1)

print("✓ Conectado! A capturar frame...")

# Ler alguns frames para dar tempo à câmara estabilizar
for i in range(5):
    ret, frame = cap.read()
    if not ret:
        print(f"❌ Erro ao ler frame {i+1}")
        sys.exit(1)

# Capturar o frame final
ret, frame = cap.read()
cap.release()

if ret:
    output_file = "esp32_reference_frame.jpg"
    cv2.imwrite(output_file, frame)
    print(f"✓ Frame capturado e guardado em: {output_file}")
    print(f"  Tamanho: {frame.shape[1]}x{frame.shape[0]} pixels")
    print()
    print("Próximo passo:")
    print(f"  python mark_parking_spots.py --source {output_file} --output parking_spots.json")
else:
    print("❌ Erro ao capturar frame final")
    sys.exit(1)
