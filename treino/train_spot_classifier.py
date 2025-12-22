import os
from pathlib import Path
import random

import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T

CSV_PATH = "dataset/labels.csv"
MODEL_OUT = "spot_classifier.pth"
IMG_SIZE = 64
BATCH_SIZE = 64
EPOCHS = 10
VAL_SPLIT = 0.2
SEED = 42


# ---------------- Dataset ----------------
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
 T.ColorJitter(brightness=0.2, contrast=0.2),
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


# -------------- Modelo simples --------------
class SpotClassifier(nn.Module):
 def __init__(self):
 super().__init__()
 self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
 self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
 self.conv3 = nn.Conv2d(32, 64, 3, padding=1)
 self.pool = nn.MaxPool2d(2, 2)
 self.fc1 = nn.Linear(64 * (IMG_SIZE // 8) * (IMG_SIZE // 8), 128)
 self.fc2 = nn.Linear(128, 2) # 0=livre, 1=ocupado

 def forward(self, x):
 x = self.pool(F.relu(self.conv1(x))) # /2
 x = self.pool(F.relu(self.conv2(x))) # /4
 x = self.pool(F.relu(self.conv3(x))) # /8
 x = x.view(x.size(0), -1)
 x = F.relu(self.fc1(x))
 x = self.fc2(x)
 return x


def main():
 random.seed(SEED)
 torch.manual_seed(SEED)

 device = "cuda" if torch.cuda.is_available() else "cpu"
 print("Device:", device)

 # ---- carregar CSV e dividir train/val ----
 df = pd.read_csv(CSV_PATH)
 df = df.sample(frac=1, random_state=SEED).reset_index(drop=True) # shuffle

 n_total = len(df)
 n_val = int(n_total * VAL_SPLIT)
 val_df = df.iloc[:n_val].reset_index(drop=True)
 train_df = df.iloc[n_val:].reset_index(drop=True)

 print(f"Total: {n_total} | train: {len(train_df)} | val: {len(val_df)}")

 train_ds = SpotDataset(train_df, train=True)
 val_ds = SpotDataset(val_df, train=False)

 train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
 val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

 # ---- modelo / loss / optim ----
 model = SpotClassifier().to(device)
 criterion = nn.CrossEntropyLoss()
 optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

 best_val_acc = 0.0

 for epoch in range(1, EPOCHS + 1):
 # treino
 model.train()
 running_loss = 0.0
 for imgs, labels in train_loader:
 imgs, labels = imgs.to(device), labels.to(device)

 optimizer.zero_grad()
 outputs = model(imgs)
 loss = criterion(outputs, labels)
 loss.backward()
 optimizer.step()

 running_loss += loss.item() * imgs.size(0)

 epoch_loss = running_loss / len(train_ds)

 # validação
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
 print(f"Epoch {epoch}/{EPOCHS} - loss: {epoch_loss:.4f} - val_acc: {val_acc:.3f}")

 if val_acc > best_val_acc:
 best_val_acc = val_acc
 torch.save(model.state_dict(), MODEL_OUT)
 print(f" Novo melhor modelo guardado em {MODEL_OUT}")

 print("Treino concluído. Melhor val_acc:", best_val_acc)


if __name__ == "__main__":
 main()
