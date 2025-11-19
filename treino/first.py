import cv2
import numpy as np
import json
from pathlib import Path

VIDEO = "video.mp4"
SPOTS_JSON = "parking_spots.json"
OUT_DIR = Path("dataset/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# carregar vagas + tamanho de referência
with open(SPOTS_JSON, "r", encoding="utf-8") as f:
    payload = json.load(f)

raw_spots = payload["spots"]
ref = payload.get("reference_size", None)

cap = cv2.VideoCapture(VIDEO)
ret, frame = cap.read()
if not ret:
    raise RuntimeError("Nao foi possivel ler o primeiro frame do video")

frame_h, frame_w = frame.shape[:2]

# calcular escala (igual ao monitor_parking_yolo.py)
if ref is not None:
    ref_w = ref["width"]
    ref_h = ref["height"]
    scale_x = frame_w / ref_w
    scale_y = frame_h / ref_h
    print(f"Escala spots: sx={scale_x:.3f}, sy={scale_y:.3f}")
else:
    scale_x = scale_y = 1.0
    print("WARNING: reference_size nao encontrado, assumindo spots ja na escala correta")

# preparar lista de spots já escalados
spots = []
for s in raw_spots:
    pts = np.array([[p["x"], p["y"]] for p in s["points"]], dtype=np.float32)
    pts[:, 0] *= scale_x
    pts[:, 1] *= scale_y
    pts_int = pts.astype(np.int32)
    spots.append({"name": s["name"], "pts": pts_int})

# voltar ao início do vídeo
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_idx % 10 != 0:  # de 10 em 10 frames
        frame_idx += 1
        continue

    h, w = frame.shape[:2]

    for spot in spots:
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [spot["pts"]], 255)

        # aplicar máscara
        spot_img = cv2.bitwise_and(frame, frame, mask=mask)

        x, y, w_box, h_box = cv2.boundingRect(spot["pts"])
        spot_crop = spot_img[y:y+h_box, x:x+w_box]

        if spot_crop.size == 0:
            continue

        # para guardar para rotular, podes manter maior (ex: 128x128)
        spot_crop = cv2.resize(spot_crop, (128, 128))
        out_name = OUT_DIR / f"{spot['name']}_f{frame_idx:05d}.png"
        cv2.imwrite(str(out_name), spot_crop)

    frame_idx += 1

cap.release()
print("Extraction done.")
