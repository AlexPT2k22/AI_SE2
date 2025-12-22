"""
Script para re-treinar o modelo CNN com o novo dataset do ESP32.
Funciona tanto com o dataset interativo como com um dataset já existente.
"""
import os
import random
from pathlib import Path

import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T

# Configurações
DATASET_DIR = "dataset_esp32"
CSV_PATH = f"{DATASET_DIR}/labels.csv"
MODEL_OUT = "spot_classifier.pth"
BACKUP_MODEL = "spot_classifier_backup.pth"
IMG_SIZE = 64
BATCH_SIZE = 16
EPOCHS = 20
VAL_SPLIT = 0.2
SEED = 42

class SpotDataset(Dataset):
 def __init__(self, df: pd.DataFrame, train: bool = True):
 self.paths = df["path"].tolist()
 self.labels = df["label"].tolist()

 base_transforms = [
 T.Resize((IMG_SIZE, IMG_SIZE)),
 T.ToTensor(),
 T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
 ]

 if train:
 aug = [
 T.RandomHorizontalFlip(),
 T.RandomVerticalFlip(),
 T.RandomRotation(15),
 T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
 ]
 self.transform = T.Compose(aug + base_transforms)
 else:
 self.transform = T.Compose(base_transforms)

 def __len__(self):
 return len(self.paths)

 def __getitem__(self, idx):
 img_path = self.paths[idx]
 label = int(self.labels[idx])
 img = Image.open(img_path).convert("RGB")
 img = self.transform(img)
 return img, label


class SpotClassifier(nn.Module):
 def __init__(self):
 super().__init__()
 self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
 self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
 self.conv3 = nn.Conv2d(32, 64, 3, padding=1)
 self.pool = nn.MaxPool2d(2, 2)
 self.fc1 = nn.Linear(64 * (IMG_SIZE // 8) * (IMG_SIZE // 8), 128)
 self.fc2 = nn.Linear(128, 2)

 def forward(self, x):
 x = self.pool(F.relu(self.conv1(x)))
 x = self.pool(F.relu(self.conv2(x)))
 x = self.pool(F.relu(self.conv3(x)))
 x = x.view(x.size(0), -1)
 x = F.relu(self.fc1(x))
 x = self.fc2(x)
 return x


def create_dataset_from_folders():
 """Cria CSV a partir de pastas free/ e occupied/"""
 rows = []
 
 free_dir = Path(DATASET_DIR) / "free"
 occupied_dir = Path(DATASET_DIR) / "occupied"
 
 if free_dir.exists():
 for img_path in free_dir.glob("*.png"):
 rows.append({"path": str(img_path), "label": 0})
 for img_path in free_dir.glob("*.jpg"):
 rows.append({"path": str(img_path), "label": 0})
 
 if occupied_dir.exists():
 for img_path in occupied_dir.glob("*.png"):
 rows.append({"path": str(img_path), "label": 1})
 for img_path in occupied_dir.glob("*.jpg"):
 rows.append({"path": str(img_path), "label": 1})
 
 df = pd.DataFrame(rows)
 df.to_csv(CSV_PATH, index=False)
 return df


def main():
 print("\n" + "="*60)
 print(" RE-TREINAR MODELO CNN PARA NOVO PARQUE")
 print("="*60)
 
 random.seed(SEED)
 torch.manual_seed(SEED)
 
 device = "cuda" if torch.cuda.is_available() else "cpu"
 print(f"\n Device: {device}")
 
 # Verificar/criar dataset
 if not os.path.exists(CSV_PATH):
 print(f"\n CSV não encontrado. A criar a partir de pastas...")
 df = create_dataset_from_folders()
 else:
 df = pd.read_csv(CSV_PATH)
 
 if len(df) == 0:
 print(" Dataset vazio! Executa primeiro: python prepare_dataset.py")
 return
 
 # Verificar ficheiros existem
 valid_rows = []
 for _, row in df.iterrows():
 if os.path.exists(row["path"]):
 valid_rows.append(row)
 else:
 print(f" Ficheiro não encontrado: {row['path']}")
 
 df = pd.DataFrame(valid_rows)
 
 if len(df) < 4:
 print(f" Dataset muito pequeno ({len(df)} amostras)")
 print(" Precisas de pelo menos 4 amostras para treinar")
 return
 
 # Shuffle e split
 df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
 n_val = max(1, int(len(df) * VAL_SPLIT))
 val_df = df.iloc[:n_val].reset_index(drop=True)
 train_df = df.iloc[n_val:].reset_index(drop=True)
 
 print(f"\n Dataset:")
 print(f" Total: {len(df)}")
 print(f" Treino: {len(train_df)}")
 print(f" Validação: {len(val_df)}")
 
 n_free = len(df[df["label"] == 0])
 n_occ = len(df[df["label"] == 1])
 print(f" Livres: {n_free}")
 print(f" Ocupadas: {n_occ}")
 
 if n_free == 0 or n_occ == 0:
 print("\n ATENÇÃO: Precisas de exemplos de AMBAS as classes!")
 print(" Adiciona mais imagens com prepare_dataset.py")
 
 # DataLoaders
 train_ds = SpotDataset(train_df, train=True)
 val_ds = SpotDataset(val_df, train=False)
 
 train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
 val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
 
 # Backup do modelo atual
 if os.path.exists(MODEL_OUT):
 import shutil
 shutil.copy(MODEL_OUT, BACKUP_MODEL)
 print(f"\n Backup do modelo atual: {BACKUP_MODEL}")
 
 # Modelo, loss, optimizer
 model = SpotClassifier().to(device)
 criterion = nn.CrossEntropyLoss()
 optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
 
 best_val_acc = 0.0
 
 print(f"\n Iniciando treino ({EPOCHS} épocas)...\n")
 
 for epoch in range(1, EPOCHS + 1):
 # Treino
 model.train()
 running_loss = 0.0
 correct_train = 0
 total_train = 0
 
 for imgs, labels in train_loader:
 imgs, labels = imgs.to(device), labels.to(device)
 
 optimizer.zero_grad()
 outputs = model(imgs)
 loss = criterion(outputs, labels)
 loss.backward()
 optimizer.step()
 
 running_loss += loss.item() * imgs.size(0)
 preds = outputs.argmax(dim=1)
 correct_train += (preds == labels).sum().item()
 total_train += labels.size(0)
 
 epoch_loss = running_loss / len(train_ds)
 train_acc = correct_train / total_train if total_train > 0 else 0
 
 # Validação
 model.eval()
 correct = 0
 total = 0
 with torch.no_grad():
 for imgs, labels in val_loader:
 imgs, labels = imgs.to(device), labels.to(device)
 outputs = model(imgs)
 preds = outputs.argmax(dim=1)
 correct += (preds == labels).sum().item()
 total += labels.size(0)
 
 val_acc = correct / total if total > 0 else 0
 
 print(f" Época {epoch:02d}/{EPOCHS} - Loss: {epoch_loss:.4f} - Train: {train_acc:.1%} - Val: {val_acc:.1%}", end="")
 
 if val_acc > best_val_acc:
 best_val_acc = val_acc
 torch.save(model.state_dict(), MODEL_OUT)
 print(" Melhor!")
 else:
 print()
 
 print(f"\n Treino concluído!")
 print(f" Melhor accuracy de validação: {best_val_acc:.1%}")
 print(f" Modelo guardado em: {MODEL_OUT}")
 
 print(f"\n Para testar: python test_simple.py")

if __name__ == "__main__":
 main()
