"""
Script para recolher dados de treino da ESP32-CAM.
Captura frames ao vivo e permite rotular cada vaga rapidamente.

Uso:
1. Liga a ESP32-CAM
2. Corre: python collect_training_data.py
3. Para cada vaga que aparecer, pressiona 0 (livre) ou 1 (ocupado)
4. Pressiona 'n' para capturar novo frame
5. Pressiona 'q' para sair
"""
import cv2
import numpy as np
import json
import os
import requests
from datetime import datetime
import time

# ============ CONFIGURAÇÕES ============
ESP32_URL = "http://10.114.226.15"  # IP da tua ESP32-CAM
STREAM_ENDPOINT = "/stream"  # Usar stream em vez de capture
SPOTS_FILE = "parking_spots.json"
DATASET_DIR = "dataset_esp32"

# Variável global para a stream
stream_cap = None

# ============ FUNÇÕES ============
def init_stream(url):
    """Inicializa a conexão com o stream MJPEG"""
    global stream_cap
    stream_url = f"{url}{STREAM_ENDPOINT}"
    print(f"   A conectar ao stream: {stream_url}")
    stream_cap = cv2.VideoCapture(stream_url)
    if stream_cap.isOpened():
        print("   ✅ Stream conectado!")
        return True
    else:
        print("   ❌ Falha ao conectar ao stream")
        return False

def capture_frame(url, retries=3):
    """Captura um frame do stream MJPEG"""
    global stream_cap
    
    # Se ainda não iniciou o stream, iniciar
    if stream_cap is None or not stream_cap.isOpened():
        if not init_stream(url):
            return None
    
    for attempt in range(retries):
        try:
            print(f"   Tentativa {attempt+1}/{retries}...", end=" ", flush=True)
            
            # Ler alguns frames para obter o mais recente
            for _ in range(3):
                ret, frame = stream_cap.read()
            
            if ret and frame is not None:
                print("OK!")
                return frame
            else:
                print("Frame inválido")
                # Tentar reconectar
                stream_cap.release()
                init_stream(url)
                
        except Exception as e:
            print(f"Erro: {e}")
            # Tentar reconectar
            if stream_cap:
                stream_cap.release()
            init_stream(url)
        
        if attempt < retries - 1:
            print("   A tentar novamente em 2s...")
            time.sleep(2)
    
    return None

def cleanup_stream():
    """Liberta recursos do stream"""
    global stream_cap
    if stream_cap:
        stream_cap.release()
        stream_cap = None

def load_spots():
    """Carrega as vagas do JSON"""
    with open(SPOTS_FILE, 'r') as f:
        data = json.load(f)
    return data.get("spots", []), data.get("reference_size", {})

def scale_spots(spots, ref_size, frame_size):
    """Escala as vagas para o tamanho do frame"""
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
    """Extrai crop de uma vaga"""
    x, y, w, h = cv2.boundingRect(pts)
    if w <= 0 or h <= 0:
        return None
    return frame[y:y+h, x:x+w]

def save_crop(crop, name, label, frame_id):
    """Guarda crop no directório apropriado"""
    folder = "free" if label == 0 else "occupied"
    path = f"{DATASET_DIR}/{folder}"
    os.makedirs(path, exist_ok=True)
    
    filename = f"{frame_id}_{name}.png"
    filepath = f"{path}/{filename}"
    cv2.imwrite(filepath, crop)
    return filepath

def update_csv(filepath, label):
    """Atualiza o CSV de labels"""
    csv_path = f"{DATASET_DIR}/labels.csv"
    mode = 'a' if os.path.exists(csv_path) else 'w'
    with open(csv_path, mode) as f:
        if mode == 'w':
            f.write("path,label\n")
        f.write(f"{filepath},{label}\n")

def count_samples():
    """Conta amostras existentes"""
    free = len(list((f"{DATASET_DIR}/free").split())) if os.path.exists(f"{DATASET_DIR}/free") else 0
    occ = len(list((f"{DATASET_DIR}/occupied").split())) if os.path.exists(f"{DATASET_DIR}/occupied") else 0
    
    try:
        free = len([f for f in os.listdir(f"{DATASET_DIR}/free") if f.endswith('.png')])
    except:
        free = 0
    try:
        occ = len([f for f in os.listdir(f"{DATASET_DIR}/occupied") if f.endswith('.png')])
    except:
        occ = 0
    return free, occ

def main():
    print("\n" + "="*60)
    print("   RECOLHA DE DADOS DE TREINO - ESP32-CAM")
    print("="*60)
    
    # Criar directórios
    os.makedirs(f"{DATASET_DIR}/free", exist_ok=True)
    os.makedirs(f"{DATASET_DIR}/occupied", exist_ok=True)
    
    # Carregar spots
    spots, ref_size = load_spots()
    print(f"\n✅ {len(spots)} vagas carregadas")
    
    # Testar conexão
    print(f"\n📡 A conectar à ESP32: {ESP32_URL}")
    frame = capture_frame(ESP32_URL)
    if frame is None:
        print("❌ Não foi possível conectar à ESP32!")
        print("   Verifica se o IP está correto e a ESP32 está ligada.")
        return
    
    h, w = frame.shape[:2]
    print(f"   ✅ Conectado! Frame: {w}x{h}")
    
    # Escalar spots
    scaled_spots = scale_spots(spots, ref_size, (w, h))
    
    # Contagem inicial
    n_free, n_occ = count_samples()
    print(f"\n📊 Dataset atual: {n_free} livres, {n_occ} ocupados")
    
    print("\n" + "="*60)
    print("   INSTRUÇÕES")
    print("="*60)
    print("   [n] = Capturar novo frame")
    print("   [0] = Marcar vaga como LIVRE")
    print("   [1] = Marcar vaga como OCUPADO")
    print("   [s] = Saltar esta vaga")
    print("   [q] = Sair e guardar")
    print("="*60)
    
    frame_count = 0
    total_saved = 0
    
    while True:
        # Capturar frame
        print(f"\n📸 Frame #{frame_count + 1} - A capturar...")
        frame = capture_frame(ESP32_URL)
        if frame is None:
            print("   ⚠️ Falha na captura, a tentar novamente...")
            continue
        
        frame_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        frame_count += 1
        
        # Para cada vaga
        for spot in scaled_spots:
            name = spot["name"]
            pts = spot["points"]
            
            # Extrair crop
            crop = extract_crop(frame, pts)
            if crop is None or crop.size == 0:
                print(f"   {name}: Crop vazio, saltando...")
                continue
            
            # Mostrar frame com vaga destacada
            display = frame.copy()
            cv2.polylines(display, [pts], True, (0, 255, 255), 3)
            centroid = np.mean(pts, axis=0).astype(int)
            cv2.putText(display, f"{name}", (centroid[0]-20, centroid[1]-20),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # Info na imagem
            n_free, n_occ = count_samples()
            cv2.putText(display, f"Dataset: {n_free} livres, {n_occ} ocupados", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display, f"[0]=Livre  [1]=Ocupado  [s]=Skip  [n]=Novo frame  [q]=Sair", 
                       (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            # Mostrar crop ampliado do lado
            crop_display = cv2.resize(crop, (150, 150))
            display[10:160, w-160:w-10] = crop_display
            cv2.rectangle(display, (w-162, 8), (w-8, 162), (0, 255, 255), 2)
            
            # Redimensionar para caber no ecrã
            display_resized = cv2.resize(display, (800, 600))
            cv2.imshow("Recolha de Dados", display_resized)
            
            while True:
                key = cv2.waitKey(0) & 0xFF
                
                if key == ord('0'):
                    filepath = save_crop(crop, name, 0, frame_id)
                    update_csv(filepath, 0)
                    total_saved += 1
                    print(f"   {name}: 🟢 LIVRE -> {filepath}")
                    break
                elif key == ord('1'):
                    filepath = save_crop(crop, name, 1, frame_id)
                    update_csv(filepath, 1)
                    total_saved += 1
                    print(f"   {name}: 🔴 OCUPADO -> {filepath}")
                    break
                elif key == ord('s'):
                    print(f"   {name}: ⏭️  Saltado")
                    break
                elif key == ord('n'):
                    print(f"   -> Novo frame...")
                    break
                elif key == ord('q'):
                    cv2.destroyAllWindows()
                    print(f"\n✅ Sessão terminada!")
                    n_free, n_occ = count_samples()
                    print(f"   Total guardadas: {total_saved}")
                    print(f"   Dataset: {n_free} livres, {n_occ} ocupados")
                    print(f"\n🎯 Próximo passo: python train_parking_model.py")
                    return
            
            if key == ord('n') or key == ord('q'):
                break
        
        if key == ord('q'):
            break
    
    cv2.destroyAllWindows()
    cleanup_stream()

if __name__ == "__main__":
    main()
