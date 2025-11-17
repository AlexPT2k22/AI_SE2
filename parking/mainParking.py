"""
Video parking-space occupancy checker using polygon zones defined via the picker.

This script loads the slot coordinates stored by `parkingSpacePicker.py`
and compares each polygon area from a reference image against every frame of a
video feed. Slots whose appearance differs from the empty reference beyond a
given threshold are marked as occupied.
"""

from __future__ import annotations

import argparse
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Union

import cv2
import cvzone
import numpy as np

# Legacy rectangles from earlier versions convert to polygons using this size.
FALLBACK_SLOT_SIZE = (110, 45)


def _normalize_polygons(raw_data: Iterable) -> List[List[Tuple[int, int]]]:
    polygons: List[List[Tuple[int, int]]] = []
    for entry in raw_data:
        if (
            isinstance(entry, (list, tuple))
            and len(entry) == 4
            and all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in entry)
        ):
            polygons.append([tuple(map(int, pt)) for pt in entry])
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            px, py = map(int, entry)
            w, h = FALLBACK_SLOT_SIZE
            polygons.append(
                [(px, py), (px + w, py), (px + w, py + h), (px, py + h)]
            )
    return polygons


def load_polygons(pickle_path: Path) -> List[List[Tuple[int, int]]]:
    if not pickle_path.exists():
        raise FileNotFoundError(
            f"Arquivo com as vagas nao encontrado: {pickle_path.resolve()}"
        )
    with open(pickle_path, "rb") as f:
        data = pickle.load(f)
    polygons = _normalize_polygons(data)
    if not polygons:
        raise ValueError(
            f"Nenhuma vaga encontrada em {pickle_path}. Use o picker para criar."
        )
    return polygons


@dataclass
class ParkingSlot:
    idx: int
    polygon: np.ndarray  # shape (4,2)
    rect: Tuple[int, int, int, int]  # x, y, w, h
    mask: np.ndarray  # shape (h, w)
    ref_gray: np.ndarray  # shape (h, w)
    area_px: int


def prepare_slots(
    polygons: Sequence[Sequence[Tuple[int, int]]], reference_gray: np.ndarray
) -> List[ParkingSlot]:
    slots: List[ParkingSlot] = []
    for idx, polygon in enumerate(polygons):
        pts = np.array(polygon, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)
        mask = np.zeros((h, w), dtype=np.uint8)
        shifted = pts - np.array([x, y])
        cv2.fillPoly(mask, [shifted], 255)
        ref_roi = reference_gray[y : y + h, x : x + w]
        if ref_roi.shape[:2] != (h, w):
            ref_roi = cv2.resize(ref_roi, (w, h))
        area_px = cv2.countNonZero(mask)
        slots.append(
            ParkingSlot(
                idx=idx,
                polygon=pts,
                rect=(x, y, w, h),
                mask=mask,
                ref_gray=ref_roi,
                area_px=area_px,
            )
        )
    return slots


def parse_args():
    parser = argparse.ArgumentParser(
        description="Detecta vagas livres/ocupadas em video usando zonas do picker."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Caminho para o video (ou indice da webcam, e.g. 0).",
    )
    parser.add_argument(
        "--slots",
        type=Path,
        default=Path("parking/vagas.pkl"),
        help="Arquivo pickle com os pontos das vagas.",
    )
    parser.add_argument(
        "--reference-image",
        type=Path,
        default=Path("parking/parking.png"),
        help="Imagem de referencia (estacionamento vazio) usada como baseline.",
    )
    parser.add_argument(
        "--diff-threshold",
        type=int,
        default=35,
        help="Intensidade minima de diferenca (0-255) para contar pixels como alterados.",
    )
    parser.add_argument(
        "--ratio-threshold",
        type=float,
        default=0.15,
        help="Proporcao de pixels alterados para marcar vaga como ocupada (0-1).",
    )
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Mostra janela auxiliar com o mapa de diferenca para debug.",
    )
    return parser.parse_args()


def open_video_source(source: str) -> cv2.VideoCapture:
    if len(source) == 1 and source.isdigit():
        cap = cv2.VideoCapture(int(source))
    else:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Falha ao abrir o video/camera: {source}")
    return cap


def main():
    args = parse_args()
    polygons = load_polygons(args.slots)

    ref_img = cv2.imread(str(args.reference_image))
    if ref_img is None:
        raise FileNotFoundError(
            f"Imagem de referencia nao encontrada: {args.reference_image.resolve()}"
        )
    ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)

    slots = prepare_slots(polygons, ref_gray)
    cap = open_video_source(args.video)

    win_name = "Parking Occupancy"
    diff_win = "Diff" if args.show_diff else None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame.shape[:2] != ref_img.shape[:2]:
                frame = cv2.resize(frame, (ref_img.shape[1], ref_img.shape[0]))

            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff_debug = np.zeros_like(frame_gray) if diff_win else None
            occupancies: List[bool] = []

            for slot in slots:
                x, y, w, h = slot.rect
                roi_gray = frame_gray[y : y + h, x : x + w]
                if roi_gray.shape[:2] != (h, w):
                    roi_gray = cv2.resize(roi_gray, (w, h))
                diff = cv2.absdiff(roi_gray, slot.ref_gray)
                _, thresh = cv2.threshold(
                    diff, args.diff_threshold, 255, cv2.THRESH_BINARY
                )
                diff_masked = cv2.bitwise_and(thresh, thresh, mask=slot.mask)
                active_px = cv2.countNonZero(diff_masked)
                occupied = active_px > slot.area_px * args.ratio_threshold
                occupancies.append(occupied)

                color = (0, 0, 255) if occupied else (0, 220, 0)
                cv2.polylines(frame, [slot.polygon], isClosed=True, color=color, thickness=2)
                label = "Ocupado" if occupied else "Livre"
                centroid = slot.polygon.mean(axis=0).astype(int)
                cvzone.putTextRect(
                    frame,
                    label,
                    (int(centroid[0]), int(centroid[1])),
                    scale=0.6,
                    thickness=1,
                    colorR=color,
                    colorT=(255, 255, 255),
                    offset=4,
                )

                if diff_debug is not None:
                    diff_debug[y : y + h, x : x + w] = cv2.bitwise_or(
                        diff_debug[y : y + h, x : x + w], diff_masked
                    )

            total = len(occupancies)
            occupied_count = sum(occupancies)
            free_count = total - occupied_count
            summary = f"Livres: {free_count}/{total}"
            cvzone.putTextRect(
                frame,
                summary,
                (30, 40),
                scale=0.9,
                thickness=2,
                colorR=(50, 50, 50),
                colorT=(255, 255, 255),
                offset=8,
            )

            cv2.imshow(win_name, frame)
            if diff_win and diff_debug is not None:
                cv2.imshow(diff_win, diff_debug)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
