"""
Mostra um video com as vagas (4 pontos) desenhadas por cima.

Uso:
    python visualize_spots_on_video.py --video parking/video.mp4 --spots parking_spots.json --output runs/overlays/video_spots.mp4
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Renderiza um video com as vagas pre-marcadas sobrepostas."
    )
    parser.add_argument(
        "--video",
        required=True,
        type=Path,
        help="Video de entrada (mp4, avi, etc.).",
    )
    parser.add_argument(
        "--spots",
        required=True,
        type=Path,
        help="Arquivo JSON exportado pelo mark_parking_spots.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Opcional: caminho para salvar o video anotado (ex.: runs/parking_spots_overlay.mp4).",
    )
    parser.add_argument(
        "--window-width",
        type=int,
        default=1080,
        help="Largura da janela de preview (px). Use <=0 para manter o tamanho original.",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Nao abre janela com preview; apenas salva o video (se --output estiver definido).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.35,
        help="Transparencia do preenchimento das vagas (0 a 1).",
    )
    parser.add_argument(
        "--codec",
        default="auto",
        help="FourCC usado ao salvar video (ex.: mp4v, avc1, XVID). Use 'auto' para tentar reaproveitar o codec do video original.",
    )
    return parser.parse_args()


def _resolve_reference_size(
    payload: Dict[str, object], spots_path: Path
) -> Optional[Tuple[int, int]]:
    ref = payload.get("reference_size")
    if isinstance(ref, dict) and "width" in ref and "height" in ref:
        return int(ref["width"]), int(ref["height"])

    source = payload.get("source")
    source_type = payload.get("source_type")
    if not source:
        return None

    candidate = Path(str(source))
    if not candidate.exists():
        alt = spots_path.parent / candidate
        if alt.exists():
            candidate = alt

    if not candidate.exists():
        return None

    if source_type == "image":
        img = cv2.imread(str(candidate))
        if img is not None:
            return img.shape[1], img.shape[0]
        return None

    cap = cv2.VideoCapture(str(candidate))
    if not cap.isOpened():
        return None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if width > 0 and height > 0:
        return width, height
    return None


def load_spots(spots_path: Path) -> Tuple[List[Dict[str, object]], Optional[Tuple[int, int]]]:
    if not spots_path.exists():
        raise FileNotFoundError(f"Arquivo de vagas nao encontrado em {spots_path}")
    with spots_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    spots = payload.get("spots")
    if not spots:
        raise ValueError(f"Nenhuma vaga em {spots_path}")

    parsed: List[Dict[str, object]] = []
    for entry in spots:
        points = entry.get("points", [])
        if len(points) != 4:
            raise ValueError(f"Spot {entry.get('name')} nao possui 4 pontos.")
        pts = np.array([[int(p["x"]), int(p["y"])] for p in points], dtype=np.int32)
        parsed.append({"name": entry.get("name", "spot"), "points": pts})
    reference_size = _resolve_reference_size(payload, spots_path)
    return parsed, reference_size


def _extract_input_fourcc(cap: cv2.VideoCapture) -> Optional[str]:
    code = int(cap.get(cv2.CAP_PROP_FOURCC))
    if not code:
        return None
    chars = []
    for shift in (0, 8, 16, 24):
        c = chr((code >> shift) & 0xFF)
        if not c.isprintable():
            return None
        chars.append(c)
    return "".join(chars)


def _resolve_fourcc(requested: str, cap: cv2.VideoCapture) -> str:
    requested = (requested or "").strip()
    if requested and requested.lower() != "auto":
        if len(requested) != 4:
            raise ValueError("--codec precisa conter 4 caracteres (ex.: mp4v, avc1).")
        return requested
    input_code = _extract_input_fourcc(cap)
    if input_code:
        print(f"[INFO] Reutilizando codec do video original: {input_code}")
        return input_code
    print("[WARN] Nao foi possivel descobrir o codec original. Usando mp4v.")
    return "mp4v"


def draw_spots(
    frame: np.ndarray,
    spots: List[Dict[str, object]],
    alpha: float,
    scale_x: float,
    scale_y: float,
) -> np.ndarray:
    canvas = frame.copy()
    overlay = frame.copy()

    for entry in spots:
        pts = entry["points"].astype(float)  # type: ignore[index]
        pts[:, 0] *= scale_x
        pts[:, 1] *= scale_y
        pts_int = pts.astype(np.int32)
        cv2.fillPoly(overlay, [pts_int], color=(0, 255, 0))
        cv2.polylines(overlay, [pts_int], isClosed=True, color=(0, 120, 0), thickness=2)
        centroid = pts.mean(axis=0).astype(int)
        cv2.putText(
            overlay,
            str(entry["name"]),  # type: ignore[index]
            tuple(centroid),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)
    return canvas


def main() -> None:
    args = parse_args()
    spots, reference_size = load_spots(args.spots)

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise FileNotFoundError(f"Nao foi possivel abrir o video {args.video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer: Optional[cv2.VideoWriter] = None
    writer_fourcc: Optional[str] = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        writer_fourcc = _resolve_fourcc(args.codec, cap)
        fourcc = cv2.VideoWriter_fourcc(*writer_fourcc)
        writer = cv2.VideoWriter(str(args.output), fourcc, fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError(f"Falha ao criar VideoWriter para {args.output}")

    window_name = "Parking Spots Overlay"
    target_width = args.window_width if args.window_width > 0 else None
    if not args.no_preview:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or -1
    print(
        f"[INFO] Iniciando renderizacao. Frames esperados: {frame_count if frame_count>0 else 'desconhecido'}"
    )
    print("Pressione 'q' para parar o preview.")

    scale_x = 1.0
    scale_y = 1.0
    if reference_size and reference_size[0] > 0 and reference_size[1] > 0:
        scale_x = width / reference_size[0]
        scale_y = height / reference_size[1]
        if abs(scale_x - 1.0) > 1e-3 or abs(scale_y - 1.0) > 1e-3:
            print(
                f"[INFO] Ajustando coordenadas: escala X={scale_x:.3f}, Y={scale_y:.3f} (referencia {reference_size[0]}x{reference_size[1]})"
            )
    else:
        print("[WARN] Dimensoes de referencia desconhecidas; assumindo que combinam com o video.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        annotated = draw_spots(frame, spots, alpha=args.alpha, scale_x=scale_x, scale_y=scale_y)
        if writer:
            writer.write(annotated)

        if not args.no_preview:
            display = annotated
            if target_width is not None and annotated.shape[1] != target_width:
                scale = target_width / annotated.shape[1]
                resized_h = max(1, int(annotated.shape[0] * scale))
                display = cv2.resize(annotated, (target_width, resized_h))
            cv2.imshow(window_name, display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[INFO] Preview encerrado pelo usuario.")
                break

    cap.release()
    if writer:
        writer.release()
        extra = f" (codec {writer_fourcc})" if writer_fourcc else ""
        print(f"[OK] Video anotado salvo em {args.output.resolve()}{extra}")

    if not args.no_preview:
        cv2.destroyWindow(window_name)


if __name__ == "__main__":
    main()
