import cv2
import csv
from pathlib import Path

IMAGES_DIR = Path("dataset/raw")
LABELS_FILE = Path("dataset/labels.csv")

# se não existir CSV, cria com cabeçalho
if not LABELS_FILE.exists():
 with open(LABELS_FILE, "w", newline="") as f:
 writer = csv.writer(f)
 writer.writerow(["path", "label"])

# carregar lista de imagens já rotuladas (para não repetir)
labeled_paths = set()
with open(LABELS_FILE, "r") as f:
 for line in f.readlines()[1:]:
 img_path = line.split(",")[0].strip()
 labeled_paths.add(img_path)

images = sorted([p for p in IMAGES_DIR.glob("*.png") if str(p) not in labeled_paths])

print(f"Imagens para rotular: {len(images)}")

for img_path in images:
 img = cv2.imread(str(img_path))
 if img is None:
 continue

 print(f"\nRotulando: {img_path.name}")
 print("Pressione: [o]=ocupado, [l]=livre, [q]=sair")
 
 cv2.imshow("Rotular Vaga", img)
 cv2.waitKey(1) # Atualizar janela
 
 # Loop até receber tecla válida
 while True:
 key = cv2.waitKey(0) & 0xFF
 
 if key == ord('o') or key == ord('O'):
 label = 1
 print("Marcado como OCUPADO")
 break
 elif key == ord('l') or key == ord('L'):
 label = 0
 print("Marcado como LIVRE")
 break
 elif key == ord('q') or key == ord('Q'):
 print("\n[INFO] A sair...")
 cv2.destroyAllWindows()
 exit(0)
 else:
 print(f"Tecla inválida (código: {key}). Use: o, l ou q")
 continue

 with open(LABELS_FILE, "a", newline="") as f:
 writer = csv.writer(f)
 writer.writerow([str(img_path), label])

cv2.destroyAllWindows()
