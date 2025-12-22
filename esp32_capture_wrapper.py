"""
Wrapper para ler frames da ESP32-CAM de forma compatível com OpenCV.
Usa HTTP GET requests individuais em vez de MJPEG stream.
"""
import cv2
import numpy as np
import urllib.request
import time
from typing import Optional, Tuple


class ESP32CaptureWrapper:
 """
 Classe que simula cv2.VideoCapture mas usa endpoint /capture da ESP32-CAM.
 """
 
 def __init__(self, esp32_url: str, fps: int = 10):
 """
 Args:
 esp32_url: URL base da ESP32 (ex: http://10.254.177.15)
 fps: Frames por segundo desejados
 """
 self.base_url = esp32_url.rstrip('/')
 self.capture_url = f"{self.base_url}/capture"
 self.fps = fps
 self.frame_delay = 1.0 / fps
 self.last_frame_time = 0
 self._width = 640
 self._height = 480
 self._opened = False
 
 # Testa se consegue capturar
 try:
 ret, frame = self._fetch_frame()
 if ret and frame is not None:
 self._height, self._width = frame.shape[:2]
 self._opened = True
 print(f"[INFO] ESP32 Wrapper conectado: {self._width}x{self._height}")
 else:
 print(f"[ERRO] Não conseguiu capturar da ESP32: {self.capture_url}")
 except Exception as e:
 print(f"[ERRO] Falha ao conectar à ESP32: {e}")
 
 def _fetch_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
 """Captura um frame via HTTP GET"""
 try:
 with urllib.request.urlopen(self.capture_url, timeout=5) as response:
 img_data = response.read()
 
 img_array = np.frombuffer(img_data, dtype=np.uint8)
 frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
 
 if frame is None:
 return False, None
 
 return True, frame
 
 except Exception as e:
 print(f"[WARN] Erro ao capturar frame: {e}")
 return False, None
 
 def read(self) -> Tuple[bool, Optional[np.ndarray]]:
 """
 Lê um frame (compatível com cv2.VideoCapture.read())
 Controla FPS para não sobrecarregar a ESP32
 """
 if not self._opened:
 return False, None
 
 # Controle de FPS
 now = time.time()
 elapsed = now - self.last_frame_time
 if elapsed < self.frame_delay:
 time.sleep(self.frame_delay - elapsed)
 
 ret, frame = self._fetch_frame()
 self.last_frame_time = time.time()
 
 return ret, frame
 
 def isOpened(self) -> bool:
 """Verifica se está aberto (compatível com cv2.VideoCapture)"""
 return self._opened
 
 def get(self, prop_id: int) -> float:
 """
 Retorna propriedades do vídeo (compatível com cv2.VideoCapture.get())
 """
 if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
 return float(self._width)
 elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
 return float(self._height)
 elif prop_id == cv2.CAP_PROP_FPS:
 return float(self.fps)
 return 0.0
 
 def set(self, prop_id: int, value: float) -> bool:
 """Compatibilidade com cv2.VideoCapture.set() (não implementado)"""
 return False
 
 def release(self):
 """Liberta recursos"""
 self._opened = False
 print("[INFO] ESP32 Wrapper fechado")


def get_video_capture(source):
 """
 Factory function que retorna VideoCapture apropriado.
 
 Args:
 source: Pode ser um arquivo, número de câmera, URL RTSP, ou URL ESP32
 
 Returns:
 Objeto compatível com cv2.VideoCapture
 """
 # Se for string e começar com http e contiver "10.254.177" (IP da ESP32)
 if isinstance(source, str) and source.startswith('http'):
 # Tenta primeiro com OpenCV nativo
 cap = cv2.VideoCapture(source)
 if cap.isOpened():
 # Testa se consegue ler frame
 ret, _ = cap.read()
 if ret:
 print("[INFO] Usando cv2.VideoCapture nativo para stream")
 return cap
 cap.release()
 
 # Se falhar, usa o wrapper HTTP
 print("[INFO] Stream MJPEG falhou, usando ESP32 HTTP Capture Wrapper")
 base_url = source.rsplit('/', 1)[0] # Remove /stream ou /capture
 return ESP32CaptureWrapper(base_url, fps=10)
 
 # Para arquivos locais ou outras fontes, usa OpenCV normal
 return cv2.VideoCapture(source)
