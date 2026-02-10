"""
Script simplificado de teste - analisa apenas a imagem de referência
"""
import cv2
import numpy as np
import json
import torch
import torchvision.transforms as T
from PIL import Image
from spot_classifier import SpotClassifier

# Configurações
SPOTS_FILE = "parking_spots.json"
MODEL_FILE = "spot_classifier.pth"
REFERENCE_IMAGE = "esp32_reference_frame.jpg"
IMG_SIZE = 64
SPOT_THRESHOLD = 0.7

print("\n" + "="*60)
print("   TESTE SIMPLIFICADO - ANÁLISE DA IMAGEM DE REFERÊNCIA")
print("="*60)

# 1. Carregar imagem
print(f"\n1. Carregando imagem: {REFERENCE_IMAGE}")
frame = cv2.imread(REFERENCE_IMAGE)
if frame is None:
    print("   ERRO: Não foi possível carregar a imagem!")
    exit(1)
h, w = frame.shape[:2]
print(f"   OK - Tamanho: {w}x{h}")

# 2. Carregar vagas
print(f"\n2. Carregando vagas: {SPOTS_FILE}")
with open(SPOTS_FILE, 'r') as f:
    data = json.load(f)
spots = data.get("spots", [])
ref_size = data.get("reference_size", {"width": w, "height": h})
print(f"   OK - {len(spots)} vagas encontradas")

# 3. Escalar vagas
print(f"\n3. Escalando vagas...")
ref_w, ref_h = ref_size.get("width", w), ref_size.get("height", h)
scale_x, scale_y = w / ref_w, h / ref_h
print(f"   Ref: {ref_w}x{ref_h}, Frame: {w}x{h}, Scale: {scale_x:.2f}x{scale_y:.2f}")

scaled_spots = []
for spot in spots:
    pts = []
    for p in spot.get("points", []):
        pts.append([int(p["x"] * scale_x), int(p["y"] * scale_y)])
    scaled_spots.append({"name": spot["name"], "points": np.array(pts, dtype=np.int32)})

# 4. Carregar modelo
print(f"\n4. Carregando modelo: {MODEL_FILE}")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"   Device: {device}")
model = SpotClassifier().to(device)
model.load_state_dict(torch.load(MODEL_FILE, map_location=device, weights_only=True))
model.eval()
print(f"   OK")

# 5. Transform
transform = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
    T.Normalize([0.5]*3, [0.5]*3)
])

# 6. Testar cada vaga
print(f"\n5. Analisando cada vaga...")
print(f"   {'Vaga':<10} {'P(Ocupado)':<15} {'Status':<10}")
print(f"   {'-'*40}")

overlay = frame.copy()
results = {}

for spot in scaled_spots:
    name = spot["name"]
    pts = spot["points"]
    
    # Extrair crop
    x, y, wc, hc = cv2.boundingRect(pts)
    crop = frame[y:y+hc, x:x+wc]
    
    if crop.size == 0:
        print(f"   {name:<10} {'N/A':<15} {'ERRO':<10}")
        continue
    
    # Guardar crop
    cv2.imwrite(f"test_crop_{name}.jpg", crop)
    
    # Classificar
    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(crop_rgb)
    tensor = transform(pil_img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        output = model(tensor)
        probs = torch.softmax(output, dim=1).cpu().numpy()[0]
    
    prob_occ = float(probs[1])
    is_occ = prob_occ >= SPOT_THRESHOLD
    status = "OCUPADO" if is_occ else "LIVRE"
    emoji = "\U0001F534" if is_occ else "\U0001F7E2"
    
    results[name] = {"prob": prob_occ, "occupied": is_occ}
    print(f"   {name:<10} {prob_occ:.4f}          {emoji} {status}")
    
    # Desenhar na imagem
    color = (0, 0, 255) if is_occ else (0, 255, 0)
    cv2.fillPoly(overlay, [pts], color)
    cv2.polylines(frame, [pts], True, color, 2)
    centroid = np.mean(pts, axis=0).astype(int)
    cv2.putText(frame, f"{name} ({prob_occ:.2f})", (centroid[0]-30, centroid[1]),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

# Blend e guardar
result = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
cv2.imwrite("test_result.jpg", result)

# Resumo
print(f"\n{'='*60}")
print(f"   RESUMO")
print(f"{'='*60}")
occupied = sum(1 for r in results.values() if r["occupied"])
print(f"   Total: {len(results)} vagas")
print(f"   Ocupadas: {occupied}")
print(f"   Livres: {len(results) - occupied}")
print(f"\n   Imagem gerada: test_result.jpg")
print(f"   Crops gerados: test_crop_*.jpg")
