"""
Monitor de estacionamento apenas com CNN por vaga (OTIMIZADO).

- Lê o vídeo
- Lê as vagas do parking_spots.json
- Escala as vagas para o tamanho do vídeo
- Para cada frame (ou de N em N frames):
    - recorta patches de TODAS as vagas
    - faz 1 forward em batch no SpotClassifier
- Suaviza no tempo (histórico por vaga)
- Desenha vagas a verde/vermelho + contador
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from collections import defaultdict, deque

import cv2
import numpy as np
import torch
from PIL import Image
import torchvision.transforms as T

from spot_classifier import SpotClassifier


Spot = Dict[str, object]
ScaledSpot = Dict[str, object]


# ------------------------------------------------------------
# Argumentos
# ------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor de estacionamento só com CNN por vaga (otimizado).")
    parser.add_argument("--video", required=True, type=Path, help="Vídeo de entrada (mp4, avi, etc.)")
    parser.add_argument("--spots", required=True, type=Path, help="Arquivo parking_spots.json")
    parser.add_argument("--model", type=Path, default=Path("spot_classifier.pth"),
                        help="Path para o modelo CNN treinado (spot_classifier.pth)")
    parser.add_argument("--output", type=Path, help="Opcional: caminho para salvar o vídeo anotado")
    parser.add_argument("--threshold", type=float, default=0.7,
                        help="Probabilidade mínima para considerar vaga ocupada (default: 0.7)")
    parser.add_argument("--alpha", type=float, default=0.35,
                        help="Transparência do preenchimento das vagas (0-1)")
    parser.add_argument("--window-width", type=int, default=960,
                        help="Largura da janela de preview (<=0 para tamanho original)")
    parser.add_argument("--no-preview", action="store_true",
                        help="Não mostra janela com preview (modo headless)")
    parser.add_argument("--history", type=int, default=5,
                        help="Comprimento do histórico por vaga para suavização (default: 5 frames)")
    parser.add_argument("--device", type=str, default=None,
                        help="Dispositivo para o CNN: 'cpu' ou 'cuda'. Default: auto")
    parser.add_argument("--frame-skip", type=int, default=2,
                        help="Processar 1 em cada N frames (default: 2 => classifica de 2 em 2 frames)")
    return parser.parse_args()


# ------------------------------------------------------------
# Device
# ------------------------------------------------------------
def get_torch_device(requested: Optional[str]) -> torch.device:
    if requested is not None:
        if requested.lower() == "cpu":
            return torch.device("cpu")
        if requested.lower().startswith("cuda") and torch.cuda.is_available():
            return torch.device("cuda")
        print("[WARN] Dispositivo pedido inválido ou CUDA indisponível. Usando CPU.")
        return torch.device("cpu")

    if torch.cuda.is_available():
        print("[INFO] Usando CUDA para o classificador.")
        return torch.device("cuda")
    print("[INFO] Usando CPU para o classificador.")
    return torch.device("cpu")


# ------------------------------------------------------------
# Carregar vagas
# ------------------------------------------------------------
def load_spots(spots_path: Path) -> Tuple[List[Spot], Optional[Tuple[int, int]]]:
    if not spots_path.exists():
        raise FileNotFoundError(f"Arquivo de vagas não encontrado: {spots_path}")

    with spots_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    raw_spots = payload.get("spots", [])
    if not raw_spots:
        raise ValueError("Nenhuma vaga encontrada no JSON.")

    parsed: List[Spot] = []
    for entry in raw_spots:
        pts = np.array([[p["x"], p["y"]] for p in entry["points"]], dtype=np.float32)
        parsed.append({"name": entry["name"], "points": pts})

    ref = payload.get("reference_size")
    if ref and "width" in ref and "height" in ref:
        reference_size = (int(ref["width"]), int(ref["height"]))
    else:
        reference_size = None

    return parsed, reference_size


# ------------------------------------------------------------
# Escalar vagas para o tamanho do vídeo
# ------------------------------------------------------------
def scale_spots(
    spots: Sequence[Spot],
    reference_size: Optional[Tuple[int, int]],
    frame_size: Tuple[int, int],
) -> List[ScaledSpot]:
    frame_w, frame_h = frame_size

    if reference_size:
        ref_w, ref_h = reference_size
        sx = frame_w / ref_w
        sy = frame_h / ref_h
        print(f"[INFO] Escalando vagas: sx={sx:.3f}, sy={sy:.3f}")
    else:
        sx = sy = 1.0
        print("[WARN] reference_size ausente no JSON. Assumindo que as vagas já estão na escala do vídeo.")

    scaled: List[ScaledSpot] = []
    for spot in spots:
        pts = spot["points"].copy()
        pts[:, 0] *= sx
        pts[:, 1] *= sy

        pts_float = pts.astype(np.float32)
        pts_int = np.round(pts_float).astype(np.int32)
        area = float(cv2.contourArea(pts_float))
        if area <= 1.0:
            print(f"[WARN] Vaga {spot['name']} com área muito pequena. Ignorando.")
            continue

        scaled.append(
            {
                "name": spot["name"],
                "points_float": pts_float,
                "points_int": pts_int,
                "area": area,
            }
        )
    return scaled


# ------------------------------------------------------------
# Cropar todas as vagas e criar batch
# ------------------------------------------------------------
def build_batch_for_frame(
    frame: np.ndarray,
    scaled_spots: Sequence[ScaledSpot],
    transform,
) -> Tuple[List[Tuple[str, np.ndarray]], Optional[torch.Tensor]]:
    """
    Devolve:
      - meta: lista de (nome, pts_int)
      - batch: tensor (N, C, H, W) ou None se N=0
    """
    h, w = frame.shape[:2]
    meta: List[Tuple[str, np.ndarray]] = []
    tensors: List[torch.Tensor] = []

    for spot in scaled_spots:
        name = spot["name"]
        pts_int = spot["points_int"]  # np.ndarray Nx2 int32

        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts_int], 255)
        masked = cv2.bitwise_and(frame, frame, mask=mask)

        x, y, w_box, h_box = cv2.boundingRect(pts_int)
        crop = masked[y:y + h_box, x:x + w_box]

        if crop.size == 0:
            continue

        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(crop)
        tensor = transform(img)  # (C,H,W)
        tensors.append(tensor)
        meta.append((name, pts_int))

    if not tensors:
        return meta, None

    batch = torch.stack(tensors, dim=0)  # (N,C,H,W)
    return meta, batch


# ------------------------------------------------------------
# Desenhar frame
# ------------------------------------------------------------
def annotate_frame(
    frame: np.ndarray,
    spots_status: Sequence[Dict[str, object]],
    alpha: float
) -> np.ndarray:
    overlay = frame.copy()

    for spot in spots_status:
        pts = spot["points"]              # np.ndarray int32 (Nx2)
        occupied = spot["occupied"]       # bool
        name = spot["name"]
        prob = spot.get("prob", 0.0)

        color = (0, 0, 255) if occupied else (0, 200, 0)
        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(frame, [pts], True, color, 2)

        cx, cy = pts.mean(axis=0).astype(int)
        label = f"{name} {prob:.2f} - {'OCUP' if occupied else 'LIVRE'}"
        cv2.putText(
            frame,
            label,
            (cx - 40, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    return frame


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main() -> None:
    args = parse_args()

    torch_device = get_torch_device(args.device)

    # carregar vagas
    base_spots, reference_size = load_spots(args.spots)

    # abrir vídeo
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise FileNotFoundError(f"Não foi possível abrir o vídeo: {args.video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"[INFO] Vídeo: {frame_w}x{frame_h} @ {fps:.2f} fps")

    scaled_spots = scale_spots(base_spots, reference_size, (frame_w, frame_h))
    if not scaled_spots:
        raise RuntimeError("Nenhuma vaga válida após escalonamento.")

    total_spots = len(scaled_spots)
    print(f"[INFO] Total de vagas: {total_spots}")

    # preparar output
    writer = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(args.output), fourcc, fps, (frame_w, frame_h))
        if not writer.isOpened():
            raise RuntimeError(f"Falha ao abrir VideoWriter para {args.output}")

    # preparar janela
    window_name = "Parking Monitor - CNN only (batch)"
    target_width = args.window_width if args.window_width > 0 else None
    if not args.no_preview:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # carregar classificador
    if not args.model.exists():
        raise FileNotFoundError(f"Modelo CNN não encontrado em {args.model}")

    clf = SpotClassifier().to(torch_device)
    clf.load_state_dict(torch.load(args.model, map_location=torch_device))
    clf.eval()

    transform = T.Compose([
        T.Resize((64, 64)),
        T.ToTensor(),
        T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    threshold = args.threshold
    history_len = max(1, args.history)
    frame_skip = max(1, args.frame_skip)

    # histórico por vaga: name -> deque de ints (0/1)
    history = defaultdict(lambda: deque(maxlen=history_len))

    def smoothed_occupied(name: str, new_val: bool) -> bool:
        dq = history[name]
        dq.append(1 if new_val else 0)
        if len(dq) == 0:
            return False
        return sum(dq) > len(dq) / 2.0

    print("[INFO] A processar frames. 'q' para sair do preview.")
    frame_idx = 0
    last_spots_status: Optional[List[Dict[str, object]]] = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        recompute = (frame_idx == 1) or (frame_idx % frame_skip == 0)

        if recompute:
            meta, batch = build_batch_for_frame(frame, scaled_spots, transform)

            spots_status: List[Dict[str, object]] = []

            if batch is not None:
                batch = batch.to(torch_device)

                with torch.no_grad():
                    logits = clf(batch)
                    probs = torch.softmax(logits, dim=1).cpu().numpy()  # (N,2)

                for i, (name, pts_int) in enumerate(meta):
                    prob_occ = float(probs[i, 1])
                    raw_occupied = prob_occ >= threshold
                    final_occupied = smoothed_occupied(name, raw_occupied)

                    spots_status.append(
                        {
                            "name": name,
                            "points": pts_int,
                            "occupied": final_occupied,
                            "prob": prob_occ,
                        }
                    )
            else:
                # nenhuma vaga (deveria ser raro)
                spots_status = []

            last_spots_status = spots_status

        else:
            # reaproveitar o estado do último frame calculado
            spots_status = last_spots_status or []

        occupied = sum(1 for s in spots_status if s["occupied"])
        free = total_spots - occupied

        annotated = annotate_frame(frame, spots_status, args.alpha)

        # barra de topo
        status_text = f"Frame {frame_idx} | Ocupadas: {occupied}/{total_spots} | Livres: {free}"
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 30), (0, 0, 0), -1)
        cv2.putText(
            annotated,
            status_text,
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # escrever no vídeo de saída
        if writer:
            writer.write(annotated)

        # preview
        if not args.no_preview:
            display = annotated
            if target_width is not None and annotated.shape[1] != target_width:
                scale = target_width / annotated.shape[1]
                resized_h = max(1, int(annotated.shape[0] * scale))
                display = cv2.resize(annotated, (target_width, resized_h))
            cv2.imshow(window_name, display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[INFO] Preview interrompido pelo utilizador.")
                break

    cap.release()
    if writer:
        writer.release()
    if not args.no_preview:
        cv2.destroyWindow(window_name)
    print("[INFO] Terminado.")


if __name__ == "__main__":
    main()
