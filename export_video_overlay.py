"""
Exportar video.mp4 com as marcações da CNN sobrepostas.
Vagas livres = verde, vagas ocupadas = vermelho.

Uso:
    python export_video_overlay.py
    python export_video_overlay.py --source video.mp4 --output output_overlay.mp4
"""
import cv2
import numpy as np
import json
import torch
from PIL import Image
import torchvision.transforms as T
from pathlib import Path
from collections import defaultdict, deque

from spot_classifier import SpotClassifier

# ============ CONFIG ============
VIDEO_SOURCE = "video.mp4"
SPOTS_FILE = "parking_spots.json"
MODEL_FILE = "spot_classifier.pth"
OUTPUT_FILE = "output_overlay.mp4"
IMG_SIZE = 64
SPOT_THRESHOLD = 0.65
HISTORY_LEN = 3
PROCESS_EVERY_N = 2


def load_spots(spots_path):
    with open(spots_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    spots_raw = payload["spots"]
    result = []
    for s in spots_raw:
        pts = np.array([[p["x"], p["y"]] for p in s["points"]], dtype=np.float32)
        result.append({"name": s["name"], "points": pts})
    ref = payload.get("reference_size")
    reference_size = (int(ref["width"]), int(ref["height"])) if ref else None
    return result, reference_size


def scale_spots(spots, ref_size, frame_size):
    fw, fh = frame_size
    if ref_size:
        sx = fw / ref_size[0]
        sy = fh / ref_size[1]
    else:
        sx = sy = 1.0
    scaled = []
    for spot in spots:
        pts = spot["points"].copy()
        pts[:, 0] *= sx
        pts[:, 1] *= sy
        scaled.append({"name": spot["name"], "points": np.round(pts).astype(np.int32)})
    return scaled


def build_batch(frame, scaled_spots, transform):
    h, w = frame.shape[:2]
    meta = []
    tensors = []
    for spot in scaled_spots:
        name = spot["name"]
        pts = spot["points"]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)
        cropped = cv2.bitwise_and(frame, frame, mask=mask)
        x, y, w_box, h_box = cv2.boundingRect(pts)
        crop = cropped[y:y + h_box, x:x + w_box]
        if crop.size == 0:
            continue
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(crop)
        tensors.append(transform(img))
        meta.append((name, pts))
    if not tensors:
        return meta, None
    return meta, torch.stack(tensors, dim=0)


def draw_overlay(frame, spot_states):
    """Draw colored overlays on parking spots."""
    overlay = frame.copy()
    for name, info in spot_states.items():
        pts = info["pts"]
        occupied = info["occupied"]
        color = (0, 0, 220) if occupied else (0, 200, 0)  # Red if occupied, green if free
        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(frame, [pts], True, color, 2)
        # Label
        centroid = pts.mean(axis=0).astype(int)
        label = f"{name}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.putText(overlay, label, (centroid[0] - tw // 2, centroid[1] + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

    # Blend overlay
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    # Stats bar
    total = len(spot_states)
    occ = sum(1 for s in spot_states.values() if s["occupied"])
    free = total - occ
    bar_h = 40
    cv2.rectangle(frame, (0, 0), (frame.shape[1], bar_h), (30, 30, 30), -1)
    cv2.putText(frame, f"Smart Parking Monitor  |  {free} Free  |  {occ} Occupied  |  {total} Total",
                (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

    return frame


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=VIDEO_SOURCE)
    parser.add_argument("--output", default=OUTPUT_FILE)
    parser.add_argument("--fps", type=float, default=None, help="Output FPS (default: same as source)")
    args = parser.parse_args()

    print("=" * 60)
    print("   EXPORT VIDEO COM OVERLAY CNN")
    print("=" * 60)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n📱 Device: {device}")

    # Load model
    model = SpotClassifier()
    model.load_state_dict(torch.load(MODEL_FILE, map_location=device, weights_only=True))
    model.to(device)
    model.eval()
    print(f"✅ Modelo carregado: {MODEL_FILE}")

    # Transform
    transform = T.Compose([
        T.Resize((IMG_SIZE, IMG_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    # Load spots
    spots, ref_size = load_spots(SPOTS_FILE)
    print(f"✅ {len(spots)} vagas carregadas")

    # Open video
    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        print(f"❌ Não foi possível abrir: {args.source}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_fps = args.fps or src_fps
    print(f"📹 Input: {w}x{h}, {total_frames} frames, {src_fps:.1f} FPS")
    print(f"📹 Output: {args.output}, {out_fps:.1f} FPS")

    # Scale spots
    scaled_spots = scale_spots(spots, ref_size, (w, h))

    # Video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(args.output, fourcc, out_fps, (w, h))

    # History for smoothing
    history = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
    spot_states = {}
    frame_idx = 0

    print(f"\n🚀 A processar...\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        progress = frame_idx / total_frames * 100

        # Process every N frames
        if frame_idx % PROCESS_EVERY_N == 0 or frame_idx == 1:
            meta, batch = build_batch(frame, scaled_spots, transform)

            if batch is not None:
                batch = batch.to(device)
                with torch.no_grad():
                    preds = model(batch)
                    probs = torch.softmax(preds, dim=1).cpu().numpy()

                for i, (name, pts) in enumerate(meta):
                    p_occ = float(probs[i][1])
                    occ_raw = (p_occ >= SPOT_THRESHOLD)
                    history[name].append(1 if occ_raw else 0)
                    occ_final = (sum(history[name]) > len(history[name]) / 2)
                    spot_states[name] = {"pts": pts, "occupied": occ_final, "confidence": p_occ}

        # Draw overlay
        if spot_states:
            frame = draw_overlay(frame, spot_states)

        writer.write(frame)

        if frame_idx % 50 == 0 or frame_idx == total_frames:
            bar_len = 30
            filled = int(bar_len * progress / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r  [{bar}] {progress:.0f}% ({frame_idx}/{total_frames})", end="", flush=True)

    cap.release()
    writer.release()

    print(f"\n\n🎉 Vídeo exportado: {args.output}")
    print(f"   {frame_idx} frames processados")
    
    # Filesize
    size_mb = Path(args.output).stat().st_size / (1024 * 1024)
    print(f"   Tamanho: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
