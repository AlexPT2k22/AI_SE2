# Exemplo de como o ESP32 deve enviar requisições para as rotas /api/entry e /api/exit

## POST /api/entry
O ESP32 deve enviar um `multipart/form-data` com:
- `camera_id` (text): ID da câmera (ex: "gate-entrada")
- `image` (file): Imagem JPEG da matrícula

### Exemplo com curl:
```bash
curl -X POST "http://localhost:8000/api/entry" \
  -F "camera_id=gate-entrada" \
  -F "image=@matricula.jpg"
```

### Exemplo com Python (para testar):
```python
import requests

url = "http://localhost:8000/api/entry"

# Ler imagem
with open("matricula.jpg", "rb") as f:
    files = {"image": ("matricula.jpg", f, "image/jpeg")}
    data = {"camera_id": "gate-entrada"}
    
    response = requests.post(url, files=files, data=data)
    print(response.json())
```

### Resposta (sucesso):
```json
{
  "session_id": 1,
  "entry_time": "2025-11-26T20:30:15.123456+00:00",
  "plate": "AB-12-CD",
  "camera_id": "gate-entrada"
}
```

### Resposta (erro - sem matrícula detectada):
```json
{
  "detail": "Nenhuma matricula detectada na imagem."
}
```

---

## POST /api/exit
Mesma estrutura do `/api/entry`:
- `camera_id` (text): ID da câmera (ex: "gate-saida"  
- `image` (file): Imagem JPEG da matrícula

### Exemplo com curl:
```bash
curl -X POST "http://localhost:8000/api/exit" \
  -F "camera_id=gate-saida" \
  -F "image=@matricula.jpg"
```

### Resposta (sucesso):
```json
{
  "session_id": 1,
  "plate": "AB-12-CD",
  "entry_time": "2025-11-26T20:30:15.123456+00:00",
  "exit_time": "2025-11-26T21:15:30.789012+00:00",
  "amount_due": 0.68,
  "camera_id": "gate-saida"
}
```

### Resposta (erro - sessão não encontrada):
```json
{
  "detail": "Nenhuma sessao aberta encontrada para esta placa."
}
```

---

## POST /api/payments
Esta rota continua com JSON (não usa imagem):

### Exemplo com curl:
```bash
curl -X POST "http://localhost:8000/api/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "amount": 0.68,
    "method": "card"
  }'
```

### Resposta (sucesso):
```json
{
  "session_id": 1,
  "amount_paid": 0.68,
  "amount_due": 0.68,
  "status": "paid",
  "payment_method": "card",
  "payment_amount": 0.68
}
```

---

## Notas importantes para o ESP32:

1. **Formato da imagem**: JPEG é recomendado para economizar largura de banda
2. **Tamanho da imagem**: Redimensionar para ~640x480 ou menor antes de enviar
3. **Qualidade JPEG**: 70-80% é suficiente para boa detecção
4. **Iluminação**: Certifique-se de que a matrícula está bem iluminada
5. **Foco**: A matrícula deve estar em foco e legível
6. **HTTP Content-Type**: Deve ser `multipart/form-data`
7. **Timeout**: Configure timeout de pelo menos 5-10 segundos (ALPR pode demorar)
