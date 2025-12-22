"""
Script de diagnóstico para testar a integração ESP32-CAM + Backend.
Verifica:
1. Conexão à ESP32-CAM
2. Captura de frame
3. Carregamento das vagas do parking_spots.json
4. Classificação de cada vaga (livre/ocupado)
5. Visualização das vagas na imagem
"""
import cv2
import numpy as np
import json
import urllib.request
import sys
from pathlib import Path
import torch
import torchvision.transforms as T
from PIL import Image

# Importar o classificador
from spot_classifier import SpotClassifier

# Configurações
ESP32_URL = "http://10.254.177.15" # Altere para o IP da sua ESP32
SPOTS_FILE = "parking_spots.json"
MODEL_FILE = "spot_classifier.pth"
IMG_SIZE = 64
SPOT_THRESHOLD = 0.7 # Limiar para considerar ocupado

def test_esp32_connection(url: str) -> bool:
 """Testa conexão à ESP32-CAM"""
 print(f"\n{'='*50}")
 print("1. TESTANDO CONEXÃO À ESP32-CAM")
 print(f"{'='*50}")
 
 try:
 capture_url = f"{url}/capture"
 print(f" URL: {capture_url}")
 
 with urllib.request.urlopen(capture_url, timeout=10) as response:
 data = response.read()
 print(f" Conexão OK! Recebidos {len(data)} bytes")
 return True
 except Exception as e:
 print(f" ERRO: {e}")
 print(f" Verifique se a ESP32 está ligada e o IP está correto")
 return False

def capture_frame(url: str) -> np.ndarray:
 """Captura um frame da ESP32-CAM"""
 print(f"\n{'='*50}")
 print("2. CAPTURANDO FRAME")
 print(f"{'='*50}")
 
 try:
 capture_url = f"{url}/capture"
 with urllib.request.urlopen(capture_url, timeout=10) as response:
 img_data = response.read()
 
 img_array = np.frombuffer(img_data, dtype=np.uint8)
 frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
 
 if frame is None:
 print(" Não conseguiu decodificar a imagem")
 return None
 
 h, w = frame.shape[:2]
 print(f" Frame capturado: {w}x{h} pixels")
 
 # Guardar para debug
 cv2.imwrite("test_captured_frame.jpg", frame)
 print(f" Guardado em: test_captured_frame.jpg")
 
 return frame
 
 except Exception as e:
 print(f" ERRO ao capturar: {e}")
 return None

def load_spots(spots_file: str) -> tuple:
 """Carrega as vagas do JSON"""
 print(f"\n{'='*50}")
 print("3. CARREGANDO VAGAS DO JSON")
 print(f"{'='*50}")
 
 try:
 with open(spots_file, 'r') as f:
 data = json.load(f)
 
 spots = data.get("spots", [])
 ref_size = data.get("reference_size", {})
 source = data.get("source", "desconhecido")
 
 print(f" Fonte: {source}")
 print(f" Tamanho de referência: {ref_size.get('width', '?')}x{ref_size.get('height', '?')}")
 print(f" Número de vagas: {len(spots)}")
 
 for spot in spots:
 pts = spot.get("points", [])
 print(f" - {spot['name']}: {len(pts)} pontos")
 
 return spots, ref_size
 
 except Exception as e:
 print(f" ERRO ao carregar: {e}")
 return [], {}

def scale_spots(spots, ref_size, frame_size):
 """Escala as vagas para o tamanho do frame atual"""
 print(f"\n{'='*50}")
 print("4. ESCALANDO VAGAS PARA O FRAME ATUAL")
 print(f"{'='*50}")
 
 ref_w = ref_size.get("width", frame_size[0])
 ref_h = ref_size.get("height", frame_size[1])
 
 scale_x = frame_size[0] / ref_w
 scale_y = frame_size[1] / ref_h
 
 print(f" Referência: {ref_w}x{ref_h}")
 print(f" Frame atual: {frame_size[0]}x{frame_size[1]}")
 print(f" Fator de escala: {scale_x:.3f}x, {scale_y:.3f}y")
 
 scaled = []
 for spot in spots:
 pts = []
 for p in spot.get("points", []):
 x = int(p["x"] * scale_x)
 y = int(p["y"] * scale_y)
 pts.append([x, y])
 
 scaled.append({
 "name": spot["name"],
 "points": np.array(pts, dtype=np.int32),
 })
 
 return scaled

def extract_crop(frame, pts):
 """Extrai o crop de uma vaga"""
 x, y, w, h = cv2.boundingRect(pts)
 if w <= 0 or h <= 0:
 return None
 return frame[y:y+h, x:x+w].copy()

def test_classifier(frame, scaled_spots, model_file):
 """Testa o classificador em cada vaga"""
 print(f"\n{'='*50}")
 print("5. TESTANDO CLASSIFICADOR CNN")
 print(f"{'='*50}")
 
 # Carregar modelo
 try:
 device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
 print(f" Dispositivo: {device}")
 
 model = SpotClassifier().to(device)
 model.load_state_dict(torch.load(model_file, map_location=device))
 model.eval()
 print(f" Modelo carregado: {model_file}")
 except Exception as e:
 print(f" ERRO ao carregar modelo: {e}")
 return {}
 
 # Transform
 transform = T.Compose([
 T.Resize((IMG_SIZE, IMG_SIZE)),
 T.ToTensor(),
 T.Normalize([0.5]*3, [0.5]*3)
 ])
 
 results = {}
 
 print(f"\n Threshold: {SPOT_THRESHOLD}")
 print(f" {'Vaga':<10} {'Prob Ocupado':<15} {'Status':<10}")
 print(f" {'-'*40}")
 
 for spot in scaled_spots:
 name = spot["name"]
 pts = spot["points"]
 
 # Extrair crop
 crop = extract_crop(frame, pts)
 if crop is None or crop.size == 0:
 print(f" {name:<10} {'N/A':<15} {'ERRO':<10}")
 continue
 
 # Converter para PIL e aplicar transform
 try:
 crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
 pil_img = Image.fromarray(crop_rgb)
 tensor = transform(pil_img).unsqueeze(0).to(device)
 
 # Inferência
 with torch.no_grad():
 output = model(tensor)
 probs = torch.softmax(output, dim=1).cpu().numpy()[0]
 
 prob_occupied = float(probs[1])
 is_occupied = prob_occupied >= SPOT_THRESHOLD
 status = "OCUPADO" if is_occupied else "LIVRE"
 
 results[name] = {
 "prob": prob_occupied,
 "occupied": is_occupied
 }
 
 # Guardar crop para debug
 cv2.imwrite(f"test_crop_{name}.jpg", crop)
 
 status_emoji = "" if is_occupied else ""
 print(f" {name:<10} {prob_occupied:<15.4f} {status_emoji} {status:<10}")
 
 except Exception as e:
 print(f" {name:<10} {'ERRO':<15} {str(e)[:20]}")
 
 return results

def visualize_results(frame, scaled_spots, results):
 """Desenha as vagas na imagem com os resultados"""
 print(f"\n{'='*50}")
 print("6. GERANDO VISUALIZAÇÃO")
 print(f"{'='*50}")
 
 output = frame.copy()
 overlay = frame.copy()
 
 for spot in scaled_spots:
 name = spot["name"]
 pts = spot["points"]
 
 info = results.get(name, {})
 prob = info.get("prob", 0)
 occupied = info.get("occupied", False)
 
 # Cores: vermelho=ocupado, verde=livre
 color = (0, 0, 255) if occupied else (0, 255, 0)
 
 # Desenhar polígono preenchido
 cv2.fillPoly(overlay, [pts], color)
 cv2.polylines(output, [pts], True, color, 2)
 
 # Label
 centroid = np.mean(pts, axis=0).astype(int)
 label = f"{name} ({prob:.2f})"
 cv2.putText(output, label, (centroid[0]-30, centroid[1]),
 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
 
 # Blend
 result = cv2.addWeighted(overlay, 0.3, output, 0.7, 0)
 
 # Guardar
 cv2.imwrite("test_visualization.jpg", result)
 print(f" Guardado em: test_visualization.jpg")
 
 return result

def main():
 print("\n" + "="*60)
 print(" TESTE DE INTEGRAÇÃO ESP32-CAM + BACKEND")
 print("="*60)
 
 # 1. Tentar conectar à ESP32
 esp32_ok = test_esp32_connection(ESP32_URL)
 
 frame = None
 if esp32_ok:
 # 2. Capturar frame da ESP32
 frame = capture_frame(ESP32_URL)
 
 if frame is None:
 print("\n ESP32 não disponível. Usando imagem de referência...")
 ref_image = "esp32_reference_frame.jpg"
 if Path(ref_image).exists():
 frame = cv2.imread(ref_image)
 print(f" Carregada imagem de referência: {ref_image}")
 else:
 print(f" Imagem de referência não encontrada!")
 sys.exit(1)
 
 # 3. Carregar vagas
 spots, ref_size = load_spots(SPOTS_FILE)
 if not spots:
 print(" Nenhuma vaga encontrada!")
 sys.exit(1)
 
 # 4. Escalar vagas
 h, w = frame.shape[:2]
 scaled_spots = scale_spots(spots, ref_size, (w, h))
 
 # 5. Testar classificador
 results = test_classifier(frame, scaled_spots, MODEL_FILE)
 
 # 6. Visualizar
 visualize_results(frame, scaled_spots, results)
 
 print(f"\n{'='*60}")
 print(" RESUMO")
 print(f"{'='*60}")
 
 total = len(results)
 occupied = sum(1 for r in results.values() if r.get("occupied"))
 free = total - occupied
 
 print(f" Total de vagas analisadas: {total}")
 print(f" Ocupadas: {occupied}")
 print(f" Livres: {free}")
 
 print(f"\n Ficheiros gerados:")
 print(f" - test_captured_frame.jpg (frame original)")
 print(f" - test_crop_spotXX.jpg (crops de cada vaga)")
 print(f" - test_visualization.jpg (resultado final)")
 
 print(f"\n{'='*60}")
 print(" PRÓXIMOS PASSOS")
 print(f"{'='*60}")
 print(" 1. Abra test_visualization.jpg para verificar as vagas")
 print(" 2. Verifique os crops test_crop_*.jpg")
 print(" 3. Se as probabilidades estão todas ~0.5, o modelo precisa re-treino")
 print(" 4. Se as vagas não correspondem, atualize parking_spots.json")
 print()

if __name__ == "__main__":
 main()
