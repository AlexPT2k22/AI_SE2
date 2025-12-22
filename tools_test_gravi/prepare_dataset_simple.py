"""
Versão simplificada para criar dataset usando a imagem de referência.
Não precisa de conexão à ESP32.
"""
import cv2
import numpy as np
import json
import os
from pathlib import Path

# Configurações
SPOTS_FILE = "parking_spots.json"
REFERENCE_IMAGE = "esp32_reference_frame.jpg"
OUTPUT_DIR = "dataset_esp32"

def load_spots():
 """Carrega as vagas do JSON"""
 with open(SPOTS_FILE, 'r') as f:
 data = json.load(f)
 return data.get("spots", []), data.get("reference_size", {})

def main():
 print("\n" + "="*60)
 print(" PREPARAR DATASET - VERSÃO SIMPLES")
 print("="*60)
 
 # Criar diretórios
 os.makedirs(f"{OUTPUT_DIR}/free", exist_ok=True)
 os.makedirs(f"{OUTPUT_DIR}/occupied", exist_ok=True)
 
 # Carregar imagem
 print(f"\n A carregar: {REFERENCE_IMAGE}")
 frame = cv2.imread(REFERENCE_IMAGE)
 if frame is None:
 print(f" Erro: Não foi possível carregar {REFERENCE_IMAGE}")
 return
 
 h, w = frame.shape[:2]
 print(f" Tamanho: {w}x{h}")
 
 # Carregar spots
 spots, ref_size = load_spots()
 print(f"\n {len(spots)} vagas carregadas")
 
 ref_w = ref_size.get("width", w)
 ref_h = ref_size.get("height", h)
 scale_x, scale_y = w / ref_w, h / ref_h
 
 print("\n" + "="*60)
 print(" INSTRUÇÕES DE ROTULAGEM")
 print("="*60)
 print(" Para cada vaga, vai aparecer uma janela")
 print(" Pressiona:")
 print(" [0] = LIVRE (vaga vazia)")
 print(" [1] = OCUPADO (carro na vaga)")
 print(" [s] = Saltar esta vaga")
 print(" [q] = Terminar")
 print("="*60)
 
 input("\nPressiona ENTER para começar...")
 
 csv_lines = ["path,label"]
 count_free = 0
 count_occ = 0
 
 for spot in spots:
 name = spot["name"]
 pts = []
 for p in spot.get("points", []):
 pts.append([int(p["x"] * scale_x), int(p["y"] * scale_y)])
 pts = np.array(pts, dtype=np.int32)
 
 # Extrair crop
 x, y, wc, hc = cv2.boundingRect(pts)
 if wc <= 0 or hc <= 0:
 print(f" {name}: Área inválida, a saltar...")
 continue
 
 crop = frame[y:y+hc, x:x+wc]
 
 # Mostrar frame com vaga destacada
 frame_display = frame.copy()
 cv2.polylines(frame_display, [pts], True, (0, 255, 255), 3)
 centroid = np.mean(pts, axis=0).astype(int)
 cv2.putText(frame_display, f"{name} - [0]=Livre [1]=Ocupado", 
 (centroid[0]-100, centroid[1]-10),
 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
 
 # Redimensionar para caber no ecrã
 display = cv2.resize(frame_display, (800, 600))
 
 cv2.imshow(f"Rotular: {name}", display)
 
 while True:
 key = cv2.waitKey(0) & 0xFF
 
 if key == ord('0'):
 filepath = f"{OUTPUT_DIR}/free/{name}.png"
 cv2.imwrite(filepath, crop)
 csv_lines.append(f"{filepath},0")
 count_free += 1
 print(f" {name}: LIVRE")
 break
 elif key == ord('1'):
 filepath = f"{OUTPUT_DIR}/occupied/{name}.png"
 cv2.imwrite(filepath, crop)
 csv_lines.append(f"{filepath},1")
 count_occ += 1
 print(f" {name}: OCUPADO")
 break
 elif key == ord('s'):
 print(f" {name}: Saltado")
 break
 elif key == ord('q'):
 cv2.destroyAllWindows()
 print("\n Terminado pelo utilizador")
 break
 else:
 cv2.destroyAllWindows()
 continue
 
 cv2.destroyAllWindows()
 
 if key == ord('q'):
 break
 
 # Guardar CSV
 with open(f"{OUTPUT_DIR}/labels.csv", 'w') as f:
 f.write("\n".join(csv_lines))
 
 print("\n" + "="*60)
 print(" RESUMO")
 print("="*60)
 print(f" Livres: {count_free}")
 print(f" Ocupadas: {count_occ}")
 print(f" Total: {count_free + count_occ}")
 print(f"\n Guardado em: {OUTPUT_DIR}/")
 
 if count_free + count_occ > 0:
 print("\n IMPORTANTE: Para bons resultados, precisas de MAIS imagens!")
 print(" Tenta mover os carrinhos e executar este script várias vezes.")
 print("\n Próximo passo: python retrain_model.py")
 else:
 print("\n Nenhuma amostra guardada.")

if __name__ == "__main__":
 main()
