"""
Ferramenta simples para marcar vagas manualmente clicando quatro pontos.

Uso:
 python mark_parking_spots.py --source parking/video_frame.jpg --output spots.json --show
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np


Point = Tuple[int, int]


def parse_args() -> argparse.Namespace:
 parser = argparse.ArgumentParser(
 description="Marca vagas clicando quatro pontos em uma imagem ou frame de video."
 )
 parser.add_argument(
 "--source",
 required=True,
 type=Path,
 help="Imagem ou video de referencia para marcar as vagas.",
 )
 parser.add_argument(
 "--frame",
 type=int,
 default=0,
 help="Indice do frame quando o --source for um video (default: 0).",
 )
 parser.add_argument(
 "--output",
 type=Path,
 default=Path("parking_spots.json"),
 help="Arquivo JSON onde as vagas serao salvas.",
 )
 parser.add_argument(
 "--label-prefix",
 default="vaga",
 help="Prefixo usado para nomear cada vaga (ex.: spot01, spot02...).",
 )
 parser.add_argument(
 "--start-index",
 type=int,
 default=1,
 help="Indice inicial para numerar as vagas.",
 )
 return parser.parse_args()


def load_frame(path: Path, frame_idx: int) -> Tuple[np.ndarray, str]:
 suffix = path.suffix.lower()
 if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
 image = cv2.imread(str(path))
 if image is None:
 raise FileNotFoundError(f"Falha ao carregar imagem {path}")
 return image, "image"

 cap = cv2.VideoCapture(str(path))
 if not cap.isOpened():
 raise FileNotFoundError(f"Falha ao abrir video {path}")
 if frame_idx < 0:
 frame_idx = 0
 cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
 ok, frame = cap.read()
 cap.release()
 if not ok or frame is None:
 raise RuntimeError(f"Nao foi possivel ler o frame {frame_idx} de {path}")
 return frame, "video"


def draw_overlay(
 base_image: np.ndarray,
 spots: List[Dict[str, List[Dict[str, int]]]],
 current_points: List[Point],
) -> np.ndarray:
 canvas = base_image.copy()
 overlay = canvas.copy()

 for idx, spot in enumerate(spots, start=1):
 pts = np.array([[p["x"], p["y"]] for p in spot["points"]], dtype=np.int32)
 cv2.fillPoly(overlay, [pts], color=(0, 255, 0))
 cv2.polylines(overlay, [pts], isClosed=True, color=(0, 120, 0), thickness=2)
 centroid = pts.mean(axis=0).astype(int)
 cv2.putText(
 overlay,
 spot["name"],
 tuple(centroid),
 cv2.FONT_HERSHEY_SIMPLEX,
 0.6,
 (255, 255, 255),
 2,
 cv2.LINE_AA,
 )

 cv2.addWeighted(overlay, 0.35, canvas, 0.65, 0, canvas)

 # pontos atuais ainda nao convertidos em vaga
 for pt in current_points:
 cv2.circle(canvas, pt, radius=6, color=(0, 0, 255), thickness=-1)

 for i in range(1, len(current_points)):
 cv2.line(canvas, current_points[i - 1], current_points[i], (0, 0, 255), 2)

 instructions = (
 "Clicks esq: adicionar ponto | Click dir: desfazer ponto | s: salvar | "
 "z: remover ultima vaga | c: limpar pontos | q: sair"
 )
 cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 30), (0, 0, 0), -1)
 cv2.putText(
 canvas,
 instructions,
 (10, 22),
 cv2.FONT_HERSHEY_SIMPLEX,
 0.5,
 (255, 255, 255),
 1,
 cv2.LINE_AA,
 )
 return canvas


def save_spots(
 output: Path,
 source: Path,
 source_type: str,
 frame_index: int,
 image_size: Tuple[int, int],
 spots: List[Dict[str, List[Dict[str, int]]]],
) -> None:
 payload = {
 "source": str(source),
 "source_type": source_type,
 "frame_index": frame_index if source_type == "video" else None,
 "spots": spots,
 "reference_size": {"width": image_size[0], "height": image_size[1]},
 }
 with output.open("w", encoding="utf-8") as f:
 json.dump(payload, f, indent=2)
 print(f"[OK] Vagas salvas em {output.resolve()}")


def main() -> None:
 args = parse_args()
 frame, source_type = load_frame(args.source, args.frame)
 print(
 "Instrucoes:\n"
 "- Clique ESQUERDO para adicionar pontos (4 pontos formam uma vaga).\n"
 "- Clique DIREITO para remover o ultimo ponto.\n"
 "- Teclas: s=salvar, z=remover ultima vaga, c=limpar pontos atuais, q=sair."
 )

 window_name = "Parking Spot Marker"
 state = {
 "spots": [], # type: List[Dict[str, List[Dict[str, int]]]]
 "current": [], # type: List[Point]
 "counter": args.start_index,
 }

 def on_mouse(event: int, x: int, y: int, flags: int, param: Dict[str, object]) -> None:
 if event == cv2.EVENT_LBUTTONDOWN:
 param["current"].append((x, y)) # type: ignore[index]
 if len(param["current"]) == 4: # type: ignore[index]
 name = f"{args.label_prefix}{param['counter']:02d}"
 points = [
 {"x": px, "y": py} for (px, py) in param["current"] # type: ignore[index]
 ]
 param["spots"].append({"name": name, "points": points}) # type: ignore[index]
 param["counter"] += 1 # type: ignore[index]
 param["current"].clear() # type: ignore[index]
 elif event == cv2.EVENT_RBUTTONDOWN and param["current"]: # type: ignore[index]
 param["current"].pop() # type: ignore[index]

 cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
 cv2.setMouseCallback(window_name, on_mouse, state)

 while True:
 canvas = draw_overlay(frame, state["spots"], state["current"])
 cv2.imshow(window_name, canvas)
 key = cv2.waitKey(16) & 0xFF

 if key == ord("q"):
 break
 if key == ord("c"):
 state["current"].clear()
 if key == ord("z") and state["spots"]:
 removed = state["spots"].pop()
 state["counter"] -= 1
 print(f"Removido {removed['name']}")
 if key == ord("s"):
 save_spots(
 args.output,
 args.source,
 source_type,
 args.frame,
 (frame.shape[1], frame.shape[0]),
 state["spots"],
 )

 cv2.destroyAllWindows()
 if state["spots"]:
 save_spots(
 args.output,
 args.source,
 source_type,
 args.frame,
 (frame.shape[1], frame.shape[0]),
 state["spots"],
 )
 else:
 print("Nenhuma vaga foi salva.")


if __name__ == "__main__":
 main()
