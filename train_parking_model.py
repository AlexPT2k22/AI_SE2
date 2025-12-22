"""
Script para treinar o modelo CNN com os dados recolhidos.
Usa data augmentation para melhorar a generalização.
Gera gráficos de treino para o artigo científico.
"""
import os
import random
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T

# ============ CONFIGURAÇÕES ============
DATASET_DIR = "dataset_esp32"
MODEL_OUT = "spot_classifier.pth"
BACKUP_MODEL = "spot_classifier_backup.pth"
HISTORY_FILE = "training_history.json"
IMG_SIZE = 64
BATCH_SIZE = 16
EPOCHS = 30
VAL_SPLIT = 0.2
SEED = 42

# ============ DATASET ============
class SpotDataset(Dataset):
 def __init__(self, paths, labels, train=True):
 self.paths = paths
 self.labels = labels

 base_transforms = [
 T.Resize((IMG_SIZE, IMG_SIZE)),
 T.ToTensor(),
 T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
 ]

 if train:
 # Data augmentation forte para dataset pequeno
 aug = [
 T.RandomHorizontalFlip(p=0.5),
 T.RandomVerticalFlip(p=0.3),
 T.RandomRotation(15),
 T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.1),
 T.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
 ]
 self.transform = T.Compose(aug + base_transforms)
 else:
 self.transform = T.Compose(base_transforms)

 def __len__(self):
 return len(self.paths)

 def __getitem__(self, idx):
 img = Image.open(self.paths[idx]).convert("RGB")
 img = self.transform(img)
 return img, self.labels[idx]

# ============ MODELO ============
class SpotClassifier(nn.Module):
 def __init__(self):
 super().__init__()
 self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
 self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
 self.conv3 = nn.Conv2d(32, 64, 3, padding=1)
 self.pool = nn.MaxPool2d(2, 2)
 self.dropout = nn.Dropout(0.3)
 self.fc1 = nn.Linear(64 * (IMG_SIZE // 8) * (IMG_SIZE // 8), 128)
 self.fc2 = nn.Linear(128, 2)

 def forward(self, x):
 x = self.pool(F.relu(self.conv1(x)))
 x = self.pool(F.relu(self.conv2(x)))
 x = self.pool(F.relu(self.conv3(x)))
 x = x.view(x.size(0), -1)
 x = self.dropout(x)
 x = F.relu(self.fc1(x))
 x = self.fc2(x)
 return x

# ============ FUNÇÃO PARA GERAR GRÁFICOS ============
def generate_training_plots(history, output_dir="."):
 """Gera gráficos de treino para o artigo científico."""
 
 epochs = history["epochs"]
 train_loss = history["train_loss"]
 train_acc = history["train_acc"]
 val_acc = history["val_acc"]
 
 # Configuração do estilo para artigo científico
 plt.style.use('seaborn-v0_8-whitegrid')
 plt.rcParams.update({
 'font.size': 12,
 'axes.labelsize': 14,
 'axes.titlesize': 14,
 'legend.fontsize': 11,
 'figure.figsize': (10, 4)
 })
 
 # Criar figura com 2 subplots lado a lado
 fig, axes = plt.subplots(1, 2, figsize=(12, 5))
 
 # ===== Gráfico 1: Loss =====
 ax1 = axes[0]
 ax1.plot(epochs, train_loss, 'b-', linewidth=2, marker='o', markersize=4, label='Training Loss')
 ax1.set_xlabel('Epoch')
 ax1.set_ylabel('Loss')
 ax1.set_title('Training Loss vs Epochs')
 ax1.legend(loc='upper right')
 ax1.grid(True, alpha=0.3)
 ax1.set_xlim(1, max(epochs))
 
 # ===== Gráfico 2: Accuracy =====
 ax2 = axes[1]
 ax2.plot(epochs, [acc * 100 for acc in train_acc], 'b-', linewidth=2, marker='o', markersize=4, label='Training Accuracy')
 ax2.plot(epochs, [acc * 100 for acc in val_acc], 'r-', linewidth=2, marker='s', markersize=4, label='Validation Accuracy')
 ax2.set_xlabel('Epoch')
 ax2.set_ylabel('Accuracy (%)')
 ax2.set_title('Training and Validation Accuracy vs Epochs')
 ax2.legend(loc='lower right')
 ax2.grid(True, alpha=0.3)
 ax2.set_xlim(1, max(epochs))
 ax2.set_ylim(0, 105)
 
 plt.tight_layout()
 
 # Guardar figura combinada
 combined_path = os.path.join(output_dir, "training_graphs_combined.png")
 plt.savefig(combined_path, dpi=300, bbox_inches='tight', facecolor='white')
 print(f"\n Gráfico combinado guardado: {combined_path}")
 
 # Guardar gráficos individuais também
 # Loss individual
 fig_loss, ax_loss = plt.subplots(figsize=(8, 6))
 ax_loss.plot(epochs, train_loss, 'b-', linewidth=2, marker='o', markersize=5)
 ax_loss.set_xlabel('Epoch')
 ax_loss.set_ylabel('Loss')
 ax_loss.set_title('Training Loss vs Epochs')
 ax_loss.grid(True, alpha=0.3)
 loss_path = os.path.join(output_dir, "training_loss.png")
 fig_loss.savefig(loss_path, dpi=300, bbox_inches='tight', facecolor='white')
 print(f" Gráfico de loss guardado: {loss_path}")
 
 # Accuracy individual
 fig_acc, ax_acc = plt.subplots(figsize=(8, 6))
 ax_acc.plot(epochs, [acc * 100 for acc in train_acc], 'b-', linewidth=2, marker='o', markersize=5, label='Training')
 ax_acc.plot(epochs, [acc * 100 for acc in val_acc], 'r-', linewidth=2, marker='s', markersize=5, label='Validation')
 ax_acc.set_xlabel('Epoch')
 ax_acc.set_ylabel('Accuracy (%)')
 ax_acc.set_title('Training and Validation Accuracy vs Epochs')
 ax_acc.legend(loc='lower right')
 ax_acc.grid(True, alpha=0.3)
 ax_acc.set_ylim(0, 105)
 acc_path = os.path.join(output_dir, "training_accuracy.png")
 fig_acc.savefig(acc_path, dpi=300, bbox_inches='tight', facecolor='white')
 print(f" Gráfico de accuracy guardado: {acc_path}")
 
 plt.close('all')
 
 return combined_path, loss_path, acc_path

# ============ MAIN ============
def main():
 print("\n" + "="*60)
 print(" TREINO DO MODELO CNN - DETEÇÃO DE VAGAS")
 print(" (Com geração de gráficos para artigo científico)")
 print("="*60)
 
 random.seed(SEED)
 torch.manual_seed(SEED)
 
 device = "cuda" if torch.cuda.is_available() else "cpu"
 print(f"\n Device: {device}")
 
 # Recolher imagens das pastas
 paths = []
 labels = []
 
 free_dir = Path(DATASET_DIR) / "free"
 occ_dir = Path(DATASET_DIR) / "occupied"
 
 if free_dir.exists():
 for f in free_dir.glob("*.png"):
 paths.append(str(f))
 labels.append(0)
 for f in free_dir.glob("*.jpg"):
 paths.append(str(f))
 labels.append(0)
 
 if occ_dir.exists():
 for f in occ_dir.glob("*.png"):
 paths.append(str(f))
 labels.append(1)
 for f in occ_dir.glob("*.jpg"):
 paths.append(str(f))
 labels.append(1)
 
 n_free = labels.count(0)
 n_occ = labels.count(1)
 
 print(f"\n Dataset encontrado:")
 print(f" Livres: {n_free}")
 print(f" Ocupados: {n_occ}")
 print(f" Total: {len(paths)}")
 
 if len(paths) < 10:
 print("\n Dataset muito pequeno!")
 print(" Precisas de pelo menos 10 imagens para treinar.")
 print(" Corre: python collect_training_data.py")
 return
 
 if n_free == 0 or n_occ == 0:
 print("\n ATENÇÃO: Precisas de imagens de AMBAS as classes!")
 print(" Corre: python collect_training_data.py")
 return
 
 # Shuffle e split
 combined = list(zip(paths, labels))
 random.shuffle(combined)
 paths, labels = zip(*combined)
 paths, labels = list(paths), list(labels)
 
 n_val = max(2, int(len(paths) * VAL_SPLIT))
 val_paths, val_labels = paths[:n_val], labels[:n_val]
 train_paths, train_labels = paths[n_val:], labels[n_val:]
 
 print(f"\n Treino: {len(train_paths)} imagens ({100-VAL_SPLIT*100:.0f}%)")
 print(f" Validação: {len(val_paths)} imagens ({VAL_SPLIT*100:.0f}%)")
 
 # DataLoaders
 train_ds = SpotDataset(train_paths, train_labels, train=True)
 val_ds = SpotDataset(val_paths, val_labels, train=False)
 
 train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
 val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
 
 # Backup do modelo atual
 if os.path.exists(MODEL_OUT):
 import shutil
 shutil.copy(MODEL_OUT, BACKUP_MODEL)
 print(f"\n Backup criado: {BACKUP_MODEL}")
 
 # Modelo
 model = SpotClassifier().to(device)
 criterion = nn.CrossEntropyLoss()
 optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
 scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
 
 best_val_acc = 0.0
 patience = 10
 no_improve = 0
 
 # ===== HISTÓRICO PARA GRÁFICOS =====
 history = {
 "epochs": [],
 "train_loss": [],
 "train_acc": [],
 "val_acc": [],
 "dataset_info": {
 "total": len(paths),
 "free": n_free,
 "occupied": n_occ,
 "train_size": len(train_paths),
 "val_size": len(val_paths)
 }
 }
 
 print(f"\n A treinar ({EPOCHS} épocas máx, early stopping={patience})...\n")
 
 for epoch in range(1, EPOCHS + 1):
 # Treino
 model.train()
 running_loss = 0.0
 correct_train = 0
 total_train = 0
 
 for imgs, lbls in train_loader:
 imgs, lbls = imgs.to(device), torch.tensor(lbls).to(device)
 
 optimizer.zero_grad()
 outputs = model(imgs)
 loss = criterion(outputs, lbls)
 loss.backward()
 optimizer.step()
 
 running_loss += loss.item() * imgs.size(0)
 preds = outputs.argmax(dim=1)
 correct_train += (preds == lbls).sum().item()
 total_train += lbls.size(0)
 
 train_acc = correct_train / total_train if total_train > 0 else 0
 epoch_loss = running_loss / len(train_ds)
 
 # Validação
 model.eval()
 correct_val = 0
 total_val = 0
 with torch.no_grad():
 for imgs, lbls in val_loader:
 imgs, lbls = imgs.to(device), torch.tensor(lbls).to(device)
 outputs = model(imgs)
 preds = outputs.argmax(dim=1)
 correct_val += (preds == lbls).sum().item()
 total_val += lbls.size(0)
 
 val_acc = correct_val / total_val if total_val > 0 else 0
 
 scheduler.step()
 
 # ===== GUARDAR NO HISTÓRICO =====
 history["epochs"].append(epoch)
 history["train_loss"].append(round(epoch_loss, 4))
 history["train_acc"].append(round(train_acc, 4))
 history["val_acc"].append(round(val_acc, 4))
 
 # Progress bar simples
 bar = "█" * int(val_acc * 20) + "░" * (20 - int(val_acc * 20))
 print(f" Época {epoch:02d}/{EPOCHS} | Loss: {epoch_loss:.4f} | Train: {train_acc:.1%} | Val: {val_acc:.1%} [{bar}]", end="")
 
 if val_acc > best_val_acc:
 best_val_acc = val_acc
 torch.save(model.state_dict(), MODEL_OUT)
 no_improve = 0
 print(" Novo melhor!")
 else:
 no_improve += 1
 print()
 
 if no_improve >= patience:
 print(f"\n Early stopping - sem melhoria há {patience} épocas")
 break
 
 # ===== GUARDAR HISTÓRICO EM JSON =====
 history["final_results"] = {
 "best_val_acc": round(best_val_acc, 4),
 "final_train_acc": round(train_acc, 4),
 "total_epochs": epoch,
 "timestamp": datetime.now().isoformat()
 }
 
 with open(HISTORY_FILE, 'w') as f:
 json.dump(history, f, indent=2)
 print(f"\n Histórico guardado: {HISTORY_FILE}")
 
 # ===== GERAR GRÁFICOS =====
 print("\n A gerar gráficos para o artigo científico...")
 try:
 generate_training_plots(history)
 except Exception as e:
 print(f" Erro ao gerar gráficos: {e}")
 print(" Os dados estão guardados em training_history.json")
 
 print(f"\n Treino concluído!")
 print(f" Melhor accuracy de validação: {best_val_acc:.1%}")
 print(f" Modelo guardado: {MODEL_OUT}")
 
 if best_val_acc < 0.7:
 print(f"\n A accuracy está baixa ({best_val_acc:.1%})")
 print(" Sugestões:")
 print(" - Adiciona mais imagens com collect_training_data.py")
 print(" - Verifica se as coordenadas das vagas estão corretas")
 
 print("\n" + "="*60)
 print(" FICHEIROS GERADOS:")
 print("="*60)
 print(f" training_graphs_combined.png (para o artigo)")
 print(f" training_loss.png")
 print(f" training_accuracy.png")
 print(f" training_history.json")
 print(f" {MODEL_OUT}")
 print("="*60)

if __name__ == "__main__":
 main()
