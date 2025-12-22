#include "Arduino.h"
#include <WiFi.h>
#include "esp_camera.h"
#include <esp_http_server.h>
#include <ESP32Servo.h>

// =================== CONFIGURAÇÕES ===================
const char *ssid = "S23 FE de Alexandre";
const char *password = "alexpt2k20";

// CONFIGURAÇÕES DA SAÍDA (DIFERENTES DA ENTRADA)
const char* serverHost = "10.114.226.35";
const int serverPort = 8000;
const char* serverPath = "/api/exit";          // ← ENDPOINT DE SAÍDA
const char* cameraId = "gate-saida";           // ← IDENTIFICADOR DE SAÍDA

#define TRIGGER_PIN 14
#define SERVO_PIN 12        // Servo da barreira
Servo servoBarreira;
#define ECHO_PIN 15         // HC-SR04 Echo

// =================== CONTROLE DE ESTADO ===================
volatile bool systemBusy = false;  // Previne múltiplos triggers simultâneos

#define LED_RED_PIN 2       // LED RGB - Vermelho
#define LED_GREEN_PIN 13    // LED RGB - Verde

// =================== CONFIGURAÇÕES DO SENSOR ===================
#define DETECTION_DISTANCE 12  // Distância em cm para detectar veículo
#define DEBOUNCE_DELAY 5000     // Delay entre detecções (ms)

// =================== PINOS DO ESP32-CAM ===================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

httpd_handle_t camera_httpd = NULL;

// Declaração antecipada
void captureAndSend();
long measureDistance(); 

void flashBothLeds(int times, int delayMs){
  for (int i = 0; i < times; i++) {
    setLeds(true, true);  
    delay(delayMs);
    setLeds(false, false); 
    delay(delayMs);
  }
}

// Handler simples - apenas captura uma foto e salva
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;

  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Falha na captura");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  
  res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

// Handler para gatilho via web
static esp_err_t trigger_handler(httpd_req_t *req) {
  Serial.println("Gatilho via Web!");
  captureAndSend();
  httpd_resp_send(req, "Foto enviada para a API!", HTTPD_RESP_USE_STRLEN);
  return ESP_OK;
}

// Handler para ler distância via web
static esp_err_t distance_handler(httpd_req_t *req) {
  long dist = measureDistance();
  char response[64];
  snprintf(response, sizeof(response), "{\"distance_cm\": %ld}", dist);
  httpd_resp_set_type(req, "application/json");
  httpd_resp_send(req, response, strlen(response));
  return ESP_OK;
}

// Página inicial simples
static esp_err_t index_handler(httpd_req_t *req) {
  const char* html = 
    "<html><head><title>ESP32-CAM SAÍDA</title>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<style>"
    "body { font-family: Arial; text-align: center; padding: 20px; background: #0f1115; color: #fff; }"
    "h1 { color: #ff6b6b; }"
    "button { padding: 15px 30px; font-size: 18px; margin: 10px; border: none; border-radius: 8px; cursor: pointer; }"
    ".btn-primary { background: #ff6b6b; color: white; }"
    ".btn-success { background: #28a745; color: white; }"
    "#distance { font-size: 24px; margin: 20px; color: #ff6b6b; }"
    "</style>"
    "<script>"
    "function updateDistance() {"
    "  fetch('/distance').then(r=>r.json()).then(d=>{"
    "    document.getElementById('distance').innerText = d.distance_cm + ' cm';"
    "  });"
    "}"
    "setInterval(updateDistance, 1000);"
    "</script>"
    "</head><body onload='updateDistance()'>"
    "<h1>SAÍDA - Gate Camera</h1>"
    "<p>Modo Simples - Sensor Ultrassônico</p>"
    "<div id='distance'>-- cm</div>"
    "<button class='btn-primary' onclick=\"document.getElementById('img').src='/capture?'+Date.now()\">Atualizar Foto</button><br>"
    "<img id='img' src='/capture' style='max-width: 100%; margin-top: 20px; border-radius: 8px;'><br><br>"
    "<button class='btn-success' onclick=\"fetch('/trigger')\">Enviar para API</button>"
    "</body></html>";
  httpd_resp_send(req, html, strlen(html));
  return ESP_OK;
}

// Função auxiliar para controlar o LED RGB
void setLeds(bool red, bool green) {
  digitalWrite(LED_RED_PIN, red ? HIGH : LOW);
  digitalWrite(LED_GREEN_PIN, green ? HIGH : LOW);
}

/**
 * Mede a distância usando o sensor ultrassônico HC-SR04
 * Retorna a distância em centímetros
 */
long measureDistance() {
  // Envia pulso de 10us
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
  
  // Lê o tempo de resposta (timeout de 30ms = ~5m)
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  
  // Calcula distância: (tempo * velocidade do som) / 2
  // Velocidade do som: 343 m/s = 0.0343 cm/μs
  long distance = duration * 0.0343 / 2;
  
  // Retorna 0 se timeout ou distância inválida
  if (duration == 0 || distance > 400) {
    return 0;
  }
  
  return distance;
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  httpd_uri_t index_uri = {
    .uri = "/",
    .method = HTTP_GET,
    .handler = index_handler,
    .user_ctx = NULL
  };

  httpd_uri_t capture_uri = {
    .uri = "/capture",
    .method = HTTP_GET,
    .handler = capture_handler,
    .user_ctx = NULL
  };

  httpd_uri_t trigger_uri = {
    .uri = "/trigger",
    .method = HTTP_GET,
    .handler = trigger_handler,
    .user_ctx = NULL
  };

  httpd_uri_t distance_uri = {
    .uri = "/distance",
    .method = HTTP_GET,
    .handler = distance_handler,
    .user_ctx = NULL
  };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    httpd_register_uri_handler(camera_httpd, &trigger_uri);
    httpd_register_uri_handler(camera_httpd, &distance_uri);
    Serial.println("Servidor HTTP iniciado!");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=== ESP32-CAM SAÍDA - OV3660 ===");
  servoBarreira.attach(SERVO_PIN);
  servoBarreira.write(0);

  // Ultra sons
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Configurar LEDs 
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  setLeds(true, false);

  pinMode(4, OUTPUT);
  digitalWrite(4, LOW);

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  
  // Configuração conservadora
  if(psramFound()){
    Serial.println("PSRAM encontrada!");
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    Serial.println("ERRO: PSRAM NAO encontrada!");
    Serial.println("OV3660 precisa de PSRAM. Verifique Tools -> PSRAM -> Enabled");
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Falha ao iniciar camera! Erro: 0x%x\n", err);
    return;
  }

  // Corrigir orientação da imagem alex
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_vflip(s, 1);  // Flip vertical (imagem de cabeça para baixo)
  }

  Serial.println("Camera inicializada!");

  WiFi.begin(ssid, password);
  Serial.print("Conectando ao WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.print("Acesse: http://");
  Serial.println(WiFi.localIP());

  startCameraServer();
  
  Serial.println("=== PRONTO (SAÍDA)! ===");
}

void loop() {
  // Não processar se sistema ocupado
  if (systemBusy) {
    delay(100);
    return;
  }

  long distance = measureDistance();
  static unsigned long lastTriggerTime = 0;
  unsigned long now = millis();
  
  // Detecta veículo se distância for menor que o threshold
  if (distance > 0 && distance <= DETECTION_DISTANCE && (now - lastTriggerTime) > DEBOUNCE_DELAY) {
    lastTriggerTime = now;

    Serial.print("Veículo detectado na SAÍDA a ");
    Serial.print(distance);
    Serial.println(" cm");
    
    // Captura e envia para API
    captureAndSend();
  }

  delay(100);
}

void captureAndSend() {
  // Bloqueia novos triggers enquanto processa
  systemBusy = true;
  
  // Liga flash para melhor qualidade de imagem
  digitalWrite(4, HIGH);
  delay(1000);
  
  camera_fb_t * fb = esp_camera_fb_get();
  
  // Desliga flash
  digitalWrite(4, LOW);

  if (!fb) {
    Serial.println("Erro: esp_camera_fb_get falhou!");
    systemBusy = false;
    return;
  }
  
  Serial.printf("Foto capturada: %u bytes\n", fb->len);

  WiFiClient client;
  if (client.connect(serverHost, serverPort)) {
    Serial.println("Conectado ao servidor!");

    String boundary = "----WebKitFormBoundary" + String(millis());
    String head = "--" + boundary + "\r\n";
    head += "Content-Disposition: form-data; name=\"camera_id\"\r\n\r\n";
    head += String(cameraId) + "\r\n";
    head += "--" + boundary + "\r\n";
    head += "Content-Disposition: form-data; name=\"image\"; filename=\"capture.jpg\"\r\n";
    head += "Content-Type: image/jpeg\r\n\r\n";
    
    String tail = "\r\n--" + boundary + "--\r\n";
    uint32_t totalLen = head.length() + fb->len + tail.length();

    client.println("POST " + String(serverPath) + " HTTP/1.1");
    client.println("Host: " + String(serverHost));
    client.println("Content-Length: " + String(totalLen));
    client.println("Content-Type: multipart/form-data; boundary=" + boundary);
    client.println();
    client.print(head);
    
    client.write(fb->buf, fb->len);
    client.print(tail);
    
    // Aguarda resposta e captura status code
    unsigned long timeout = millis();
    int httpStatusCode = 0;
    String statusLine = "";
    String responseBody = "";
    bool headersPassed = false;
    bool barrierOpened = false;
    
    while (client.connected() && millis() - timeout < 10000) {
      if (client.available()) {
        String line = client.readStringUntil('\n');
        
        // Primeira linha: HTTP/1.1 200 OK ou HTTP/1.1 400 Bad Request
        if (httpStatusCode == 0 && line.startsWith("HTTP/")) {
          statusLine = line;
          int firstSpace = line.indexOf(' ');
          int secondSpace = line.indexOf(' ', firstSpace + 1);
          if (firstSpace > 0 && secondSpace > firstSpace) {
            String codeStr = line.substring(firstSpace + 1, secondSpace);
            httpStatusCode = codeStr.toInt();
            Serial.print("HTTP Status: ");
            Serial.println(httpStatusCode);
            
            // REAGE IMEDIATAMENTE ao status 200 (pagamento confirmado)
            if (httpStatusCode == 200 && !barrierOpened) {
              Serial.println("Status 200 - PAGAMENTO CONFIRMADO - ABRINDO BARREIRA");
              setLeds(false, true);  // LED Verde
              
              servoBarreira.write(90);
              Serial.println("Barreira aberta (90°)");
              
              barrierOpened = true;

            } else if (httpStatusCode >= 400) {
              // Erro - Pagamento NÃO confirmado
              Serial.println("Status erro - PAGAMENTO NÃO CONFIRMADO");
              setLeds(true, false);  // LED Vermelho
            }
          }
        }
        // Separador entre headers e body
        if (line == "\r") {
          headersPassed = true;
        } else if (headersPassed) {
          responseBody += line;
        }
      }
    }
    
    Serial.println("Resposta da API:");
    Serial.println(responseBody);
    
    // Processar resposta baseado no status code
    if (httpStatusCode == 200 && barrierOpened) {
      // HTTP 200 = Pagamento confirmado, pode sair
      Serial.println("Saída autorizada - aguardando passagem");
      
      // Aguarda veículo passar
      Serial.println("Aguardando veículo passar...");
      unsigned long startWait = millis();
      unsigned long clearStartTime = 0;
      bool vehiclePassed = false;
      const int CLEAR_CONFIRM_TIME = 2000;  // 2 segundos sem detecção = passou
      
      while (millis() - startWait < 30000) {  // Timeout 30s
        long dist = measureDistance();
        
        if (dist > DETECTION_DISTANCE || dist == 0) {
          // Veículo saiu da zona de detecção
          if (clearStartTime == 0) {
            clearStartTime = millis();
            Serial.print("Distância livre: ");
            Serial.print(dist);
            Serial.println(" cm - confirmando...");
          } else if (millis() - clearStartTime >= CLEAR_CONFIRM_TIME) {
            vehiclePassed = true;
            Serial.println("Veículo passou - confirmado!");
            break;
          }
        } else {
          // Veículo ainda na zona - reseta contador
          if (clearStartTime > 0) {
            Serial.println("Veículo ainda presente - resetando confirmação");
            clearStartTime = 0;
          }
        }
        
        delay(100);
      }
      
      if (!vehiclePassed) {
        Serial.println("Timeout - fechando por segurança");
      }
      
      // Aguarda mais 3 segundos
      Serial.println("Aguardando 3s para fechar...");
      delay(3000);
      
      // Fecha servo (0 graus)
      servoBarreira.write(0);
      setLeds(true, false);
      
      Serial.println("Barreira fechada");
      
      // Libera sistema para próxima detecção
      systemBusy = false;
      
    } else if (httpStatusCode >= 400) {
      // Erro - Pagamento não encontrado ou expirado
      Serial.println("ERRO - Saída negada");
      
      bool isNotPaid = false;
      bool isExpired = false;

      // Extrair mensagem de erro
      if (responseBody.indexOf("\"detail\"") > 0) {
        int detailStart = responseBody.indexOf("\"detail\"");
        int colonPos = responseBody.indexOf(':', detailStart);
        int valueStart = responseBody.indexOf('"', colonPos);
        int valueEnd = responseBody.indexOf('"', valueStart + 1);

        if (valueStart > 0 && valueEnd > valueStart) {
          String errorMsg = responseBody.substring(valueStart + 1, valueEnd);
          Serial.print("   Erro: ");
          Serial.println(errorMsg);

          // Detectar tipo de erro
          if (errorMsg.indexOf("pag") >= 0 || errorMsg.indexOf("paid") >= 0) {
            isNotPaid = true;
          } else if (errorMsg.indexOf("expirado") >= 0 || errorMsg.indexOf("expired") >= 0) {
            isExpired = true;
          }
        }
      }

      // Escolher tipo de pisca
      if (isExpired) {
        Serial.println("Pagamento expirado (>10min) - pisca 5 vezes");
        flashBothLeds(5, 150);
      } else if (isNotPaid) {
        Serial.println("Não pagou - pisca 3 vezes");
        flashBothLeds(3, 150);
      } else {
        Serial.println("Erro desconhecido - pisca 2 vezes");
        flashBothLeds(2, 150);
      }
      
      // Mantém LED vermelho por 3 segundos
      setLeds(true, false);
      
      // Libera sistema
      systemBusy = false;
      
    } else {
      // Sem status válido ou timeout
      Serial.println("Resposta inválida ou timeout");
      systemBusy = false;
    }
    
    client.stop();
  } else {
    Serial.println("Falha ao conectar na API");
    systemBusy = false;
  }
  
  esp_camera_fb_return(fb);
}
