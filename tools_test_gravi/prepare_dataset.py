"""
Script para preparar dataset de treino a partir das novas imagens do ESP32.

Passos:
1. Captura vários frames da ESP32 (ou usa frames de vídeo)
2. Extrai os crops de cada vaga
3. Pede ao utilizador para rotular: 0=livre, 1=ocupado
4. Guarda em formato pronto para treino
"""
import cv2
import numpy as np
import json
import os
from pathlib import Path

# Configurações
SPOTS_FILE = "parking_spots.json"
OUTPUT_DIR = "dataset_esp32"
LABELS_FILE = f"{OUTPUT_DIR}/labels.csv"

def load_spots():
 """Carrega as vagas do JSON"""
 with open(SPOTS_FILE, 'r') as f:
 data = json.load(f)
 return data.get("spots", []), data.get("reference_size", {})

def extract_crop(frame, pts):
 """Extrai o crop de uma vaga (bounding box)"""
 x, y, w, h = cv2.boundingRect(pts)
 if w <= 0 or h <= 0:
 return None
 return frame[y:y+h, x:x+w]

def label_crops_interactive(frame, spots, ref_size, frame_id):
 """
 Mostra cada crop e pede ao utilizador para rotular.
 Teclas:
 0 = Livre
 1 = Ocupado
 s = Skip
 q = Quit
 """
 h, w = frame.shape[:2]
 ref_w = ref_size.get("width", w)
 ref_h = ref_size.get("height", h)
 scale_x, scale_y = w / ref_w, h / ref_h
 
 labels = []
 
 for spot in spots:
 name = spot["name"]
 pts = []
 for p in spot.get("points", []):
 pts.append([int(p["x"] * scale_x), int(p["y"] * scale_y)])
 pts = np.array(pts, dtype=np.int32)
 
 # Extrair crop
 crop = extract_crop(frame, pts)
 if crop is None or crop.size == 0:
 print(f" {name}: Crop vazio, a saltar...")
 continue
 
 # Mostrar crop maior para facilitar rotulagem
 crop_display = cv2.resize(crop, (200, 200))
 
 # Desenhar na imagem original para mostrar qual vaga é
 frame_display = frame.copy()
 cv2.polylines(frame_display, [pts], True, (0, 255, 255), 3)
 centroid = np.mean(pts, axis=0).astype(int)
 cv2.putText(frame_display, name, (centroid[0]-20, centroid[1]),
 cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
 frame_display = cv2.resize(frame_display, (640, 480))
 
 # Combinar side-by-side
 h_crop = crop_display.shape[0]
 w_crop = crop_display.shape[1]
 combined = np.zeros((480, 640 + w_crop + 10, 3), dtype=np.uint8)
 combined[:, :640] = frame_display
 combined[140:140+h_crop, 650:650+w_crop] = crop_display
 
 # Instruções
 cv2.putText(combined, f"Vaga: {name}", (650, 120),
 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
 cv2.putText(combined, "[0] Livre", (650, 360),
 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
 cv2.putText(combined, "[1] Ocupado", (650, 400),
 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
 cv2.putText(combined, "[s] Skip [q] Quit", (650, 440),
 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
 
 cv2.imshow("Rotulagem", combined)
 
 while True:
 key = cv2.waitKey(0) & 0xFF
 if key == ord('0'):
 labels.append((name, frame_id, 0, crop))
 print(f" {name}: LIVRE")
 break
 elif key == ord('1'):
 labels.append((name, frame_id, 1, crop))
 print(f" {name}: OCUPADO")
 break
 elif key == ord('s'):
 print(f" {name}: Saltado")
 break
 elif key == ord('q'):
 cv2.destroyAllWindows()
 return labels, True # quit = True
 
 return labels, False

def main():
 print("\n" + "="*60)
 print(" PREPARAR DATASET PARA RE-TREINO")
 print("="*60)
 
 # Criar diretório de output
 os.makedirs(OUTPUT_DIR, exist_ok=True)
 os.makedirs(f"{OUTPUT_DIR}/free", exist_ok=True)
 os.makedirs(f"{OUTPUT_DIR}/occupied", exist_ok=True)
 
 # Carregar spots
 spots, ref_size = load_spots()
 print(f"\n Carregadas {len(spots)} vagas")
 
 # Perguntar fonte dos frames
 print("\nFontes disponíveis:")
 print(" 1. Usar imagem de referência (esp32_reference_frame.jpg)")
 print(" 2. Capturar da ESP32-CAM em tempo real")
 print(" 3. Usar ficheiro de vídeo")
 
 choice = input("\nEscolha [1/2/3]: ").strip()
 
 all_labels = []
 frame_count = 0
 
 if choice == "1":
 # Usar apenas a imagem de referência
 frame = cv2.imread("esp32_reference_frame.jpg")
 if frame is None:
 print(" Não foi possível carregar esp32_reference_frame.jpg")
 return
 
 print("\n A rotular vagas na imagem de referência...")
 print(" Para cada vaga, pressione 0 (livre) ou 1 (ocupado)")
 
 labels, quit_early = label_crops_interactive(frame, spots, ref_size, f"ref_{frame_count:04d}")
 all_labels.extend(labels)
 frame_count += 1
 
 elif choice == "2":
 # Capturar da ESP32
 import urllib.request
 
 esp32_url = input("URL da ESP32 [http://10.254.177.15]: ").strip() or "http://10.254.177.15"
 capture_url = f"{esp32_url}/capture"
 
 print("\nA capturar frames da ESP32...")
 print("Pressione 'n' para próximo frame, 'q' para terminar")
 
 while True:
 try:
 with urllib.request.urlopen(capture_url, timeout=10) as response:
 img_data = response.read()
 img_array = np.frombuffer(img_data, dtype=np.uint8)
 frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
 
 if frame is None:
 print(" Frame inválido")
 continue
 
 labels, quit_early = label_crops_interactive(frame, spots, ref_size, f"esp32_{frame_count:04d}")
 all_labels.extend(labels)
 frame_count += 1
 
 if quit_early:
 break
 
 except Exception as e:
 print(f" Erro: {e}")
 break
 
 elif choice == "3":
 # Usar vídeo
 video_path = input("Caminho do vídeo: ").strip()
 cap = cv2.VideoCapture(video_path)
 
 if not cap.isOpened():
 print(f" Não foi possível abrir {video_path}")
 return
 
 print("\nA processar vídeo...")
 print("A cada 30 frames, vais rotular as vagas")
 print("Pressione 'q' para terminar")
 
 frame_idx = 0
 while True:
 ret, frame = cap.read()
 if not ret:
 break
 
 if frame_idx % 30 == 0: # A cada 30 frames
 labels, quit_early = label_crops_interactive(frame, spots, ref_size, f"video_{frame_idx:05d}")
 all_labels.extend(labels)
 frame_count += 1
 
 if quit_early:
 break
 
 frame_idx += 1
 
 cap.release()
 
 cv2.destroyAllWindows()
 
 # Guardar crops e labels
 print(f"\n A guardar {len(all_labels)} amostras...")
 
 csv_lines = ["path,label"]
 for name, frame_id, label, crop in all_labels:
 folder = "free" if label == 0 else "occupied"
 filename = f"{frame_id}_{name}.png"
 filepath = f"{OUTPUT_DIR}/{folder}/{filename}"
 cv2.imwrite(filepath, crop)
 csv_lines.append(f"{filepath},{label}")
 
 # Guardar CSV
 with open(LABELS_FILE, 'w') as f:
 f.write("\n".join(csv_lines))
 
 print(f"\n Dataset guardado em {OUTPUT_DIR}/")
 print(f" - Amostras livres: {OUTPUT_DIR}/free/")
 print(f" - Amostras ocupadas: {OUTPUT_DIR}/occupied/")
 print(f" - Labels: {LABELS_FILE}")
 
 # Contar
 n_free = sum(1 for _, _, l, _ in all_labels if l == 0)
 n_occ = sum(1 for _, _, l, _ in all_labels if l == 1)
 print(f"\n Total: {len(all_labels)} amostras")
 print(f" Livres: {n_free}")
 print(f" Ocupadas: {n_occ}")
 
 if len(all_labels) > 0:
 print("\n Próximo passo: Treinar o modelo")
 print(" python retrain_model.py")

if __name__ == "__main__":
 main()
