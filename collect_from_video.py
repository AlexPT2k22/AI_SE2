"""
Recolha de dados de treino a partir de video.mp4.
Extrai frames do vídeo e permite rotular cada vaga como livre/ocupada.

Uso:
    python collect_from_video.py
    python collect_from_video.py --source outro_video.mp4 --skip 30
"""
import cv2
import numpy as np
import json
import os
from datetime import datetime

# ============ CONFIGURAÇÕES ============
VIDEO_FILE = "video.mp4"
SPOTS_FILE = "parking_spots.json"
DATASET_DIR = "dataset_esp32"
FRAME_SKIP = 60  # Saltar N frames entre cada amostra (para variedade)

# ============ FUNÇÕES ============
def load_spots():
    with open(SPOTS_FILE, 'r') as f:
        data = json.load(f)
    return data.get("spots", []), data.get("reference_size", {})


def scale_spots(spots, ref_size, frame_size):
    ref_w = ref_size.get("width", frame_size[0])
    ref_h = ref_size.get("height", frame_size[1])
    scale_x = frame_size[0] / ref_w
    scale_y = frame_size[1] / ref_h

    scaled = []
    for spot in spots:
        pts = []
        for p in spot.get("points", []):
            pts.append([int(p["x"] * scale_x), int(p["y"] * scale_y)])
        scaled.append({
            "name": spot["name"],
            "points": np.array(pts, dtype=np.int32)
        })
    return scaled


def extract_crop(frame, pts):
    x, y, w, h = cv2.boundingRect(pts)
    if w <= 0 or h <= 0:
        return None
    return frame[y:y+h, x:x+w]


def save_crop(crop, name, label, frame_id):
    folder = "free" if label == 0 else "occupied"
    path = f"{DATASET_DIR}/{folder}"
    os.makedirs(path, exist_ok=True)
    filename = f"{frame_id}_{name}.png"
    filepath = f"{path}/{filename}"
    cv2.imwrite(filepath, crop)
    return filepath


def count_samples():
    try:
        free = len([f for f in os.listdir(f"{DATASET_DIR}/free") if f.endswith(('.png', '.jpg'))])
    except FileNotFoundError:
        free = 0
    try:
        occ = len([f for f in os.listdir(f"{DATASET_DIR}/occupied") if f.endswith(('.png', '.jpg'))])
    except FileNotFoundError:
        occ = 0
    return free, occ


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=VIDEO_FILE, help="Vídeo source")
    parser.add_argument("--skip", type=int, default=FRAME_SKIP, help="Frames to skip between samples")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("   RECOLHA DE DADOS DE TREINO - VÍDEO")
    print("=" * 60)

    os.makedirs(f"{DATASET_DIR}/free", exist_ok=True)
    os.makedirs(f"{DATASET_DIR}/occupied", exist_ok=True)

    # Carregar spots
    spots, ref_size = load_spots()
    print(f"\n✅ {len(spots)} vagas carregadas de {SPOTS_FILE}")

    # Abrir vídeo
    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        print(f"❌ Não foi possível abrir: {args.source}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"   📹 Vídeo: {w}x{h}, {total_frames} frames, {fps:.1f} FPS")
    print(f"   ⏭️  A saltar {args.skip} frames entre amostras")

    scaled_spots = scale_spots(spots, ref_size, (w, h))

    n_free, n_occ = count_samples()
    print(f"\n📊 Dataset atual: {n_free} livres, {n_occ} ocupados")

    print("\n" + "=" * 60)
    print("   INSTRUÇÕES")
    print("=" * 60)
    print("   [0] = Marcar vaga como LIVRE")
    print("   [1] = Marcar vaga como OCUPADO")
    print("   [a] = Marcar TODAS as vagas deste frame como LIVRES")
    print("   [o] = Marcar TODAS as vagas deste frame como OCUPADAS")
    print("   [s] = Saltar esta vaga")
    print("   [n] = Avançar para próximo frame")
    print("   [q] = Sair")
    print("=" * 60)

    frame_count = 0
    total_saved = 0
    current_frame_idx = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
        ret, frame = cap.read()
        if not ret:
            print("\n📼 Fim do vídeo!")
            break

        frame_count += 1
        frame_id = f"vid_f{current_frame_idx:06d}"
        progress = current_frame_idx / total_frames * 100

        print(f"\n📸 Frame #{frame_count} (frame {current_frame_idx}/{total_frames}, {progress:.0f}%)")

        skip_to_next = False

        for spot in scaled_spots:
            if skip_to_next:
                break

            name = spot["name"]
            pts = spot["points"]

            crop = extract_crop(frame, pts)
            if crop is None or crop.size == 0:
                print(f"   {name}: Crop vazio, saltando...")
                continue

            # Mostrar frame com vaga destacada
            display = frame.copy()
            cv2.polylines(display, [pts], True, (0, 255, 255), 3)
            centroid = np.mean(pts, axis=0).astype(int)
            cv2.putText(display, f"{name}", (centroid[0] - 20, centroid[1] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            # Info
            n_free, n_occ = count_samples()
            cv2.putText(display, f"Frame {current_frame_idx}/{total_frames} | Dataset: {n_free} livres, {n_occ} ocupados",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display, "[0]=Livre [1]=Ocupado [a]=All Free [o]=All Occ [s]=Skip [n]=Next [q]=Quit",
                        (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # Crop ampliado
            crop_resized = cv2.resize(crop, (150, 150))
            y1, y2 = 10, 160
            x1, x2 = w - 160, w - 10
            if y2 <= display.shape[0] and x2 <= display.shape[1]:
                display[y1:y2, x1:x2] = crop_resized
                cv2.rectangle(display, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (0, 255, 255), 2)

            display_resized = cv2.resize(display, (960, 720))
            cv2.imshow("Recolha de Dados - Video", display_resized)

            while True:
                key = cv2.waitKey(0) & 0xFF

                if key == ord('0'):
                    filepath = save_crop(crop, name, 0, frame_id)
                    total_saved += 1
                    print(f"   {name}: 🟢 LIVRE -> {filepath}")
                    break
                elif key == ord('1'):
                    filepath = save_crop(crop, name, 1, frame_id)
                    total_saved += 1
                    print(f"   {name}: 🔴 OCUPADO -> {filepath}")
                    break
                elif key == ord('a'):
                    # Marcar todas as vagas deste frame como livres
                    for s in scaled_spots:
                        c = extract_crop(frame, s["points"])
                        if c is not None and c.size > 0:
                            fp = save_crop(c, s["name"], 0, frame_id)
                            total_saved += 1
                            print(f"   {s['name']}: 🟢 LIVRE -> {fp}")
                    skip_to_next = True
                    break
                elif key == ord('o'):
                    # Marcar todas as vagas deste frame como ocupadas
                    for s in scaled_spots:
                        c = extract_crop(frame, s["points"])
                        if c is not None and c.size > 0:
                            fp = save_crop(c, s["name"], 1, frame_id)
                            total_saved += 1
                            print(f"   {s['name']}: 🔴 OCUPADO -> {fp}")
                    skip_to_next = True
                    break
                elif key == ord('s'):
                    print(f"   {name}: ⏭️  Saltado")
                    break
                elif key == ord('n'):
                    skip_to_next = True
                    break
                elif key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    n_free, n_occ = count_samples()
                    print(f"\n✅ Sessão terminada!")
                    print(f"   Total guardadas: {total_saved}")
                    print(f"   Dataset: {n_free} livres, {n_occ} ocupados")
                    print(f"\n🎯 Próximo passo: python train_parking_model.py")
                    return

        current_frame_idx += args.skip

    cap.release()
    cv2.destroyAllWindows()
    n_free, n_occ = count_samples()
    print(f"\n✅ Sessão terminada!")
    print(f"   Total guardadas: {total_saved}")
    print(f"   Dataset: {n_free} livres, {n_occ} ocupados")
    print(f"\n🎯 Próximo passo: python train_parking_model.py")


if __name__ == "__main__":
    main()
