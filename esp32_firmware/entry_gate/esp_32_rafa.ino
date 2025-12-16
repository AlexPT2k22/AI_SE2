/**
 * ESP32-CAM Entry Gate - Parking System
 * 
 * Firmware para a camara de entrada do estacionamento.
 * Deteta veiculos via sensor ultrasonico, captura matricula
 * e envia para o backend para processamento ALPR.
 * 
 * Endpoints:
 *   GET /         - Pagina web de status
 *   GET /capture  - Captura frame unico
 *   GET /trigger  - Dispara captura manual
 *   GET /distance - Leitura do sensor ultrasonico
 */

#include "Arduino.h"
#include <WiFi.h>
#include "esp_camera.h"
#include <esp_http_server.h>
#include <ESP32Servo.h>

// =================== CONFIGURACOES DE REDE ===================
const char *ssid = "S23 FE de Alexandre";
const char *password = "alexpt2k20";

// =================== CONFIGURACOES DO SERVIDOR API ===================
const char* serverHost = "10.114.226.35";
const int serverPort = 8000;
const char* serverPath = "/api/entry";
const char* cameraId = "gate-entrada";

// =================== PINOS DO HARDWARE ===================
#define TRIGGER_PIN       14
#define ECHO_PIN          15
#define SERVO_PIN         12
#define LED_RED_PIN       2
#define LED_GREEN_PIN     13
#define FLASH_LED_PIN     4

// =================== CONFIGURACOES DO SENSOR ===================
#define DETECTION_DISTANCE 16    // Distancia em cm para detectar veiculo
#define DEBOUNCE_DELAY     5000 // Delay entre deteccoes (ms)

// =================== PINOS ESP32-CAM (AI-Thinker) ===================
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

// =================== VARIAVEIS GLOBAIS ===================
httpd_handle_t camera_httpd = NULL;
Servo servoBarreira;
volatile bool systemBusy = false;

// =================== DECLARACOES ===================
void captureAndSend();
long measureDistance();

// =================== FUNCOES AUXILIARES ===================
void setLeds(bool red, bool green) {
  digitalWrite(LED_RED_PIN, red ? HIGH : LOW);
  digitalWrite(LED_GREEN_PIN, green ? HIGH : LOW);
}

void flashBothLeds(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    setLeds(true, true);
    delay(delayMs);
    setLeds(false, false);
    delay(delayMs);
  }
}

long measureDistance() {
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
  
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  long distance = duration * 0.0343 / 2;
  
  if (duration == 0 || distance > 400) {
    return 0;
  }
  return distance;
}

// =================== HANDLERS HTTP ===================
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

static esp_err_t trigger_handler(httpd_req_t *req) {
  captureAndSend();
  httpd_resp_send(req, "Captura enviada para API", HTTPD_RESP_USE_STRLEN);
  return ESP_OK;
}

static esp_err_t distance_handler(httpd_req_t *req) {
  long dist = measureDistance();
  char response[64];
  snprintf(response, sizeof(response), "{\"distance_cm\": %ld}", dist);
  httpd_resp_set_type(req, "application/json");
  httpd_resp_send(req, response, strlen(response));
  return ESP_OK;
}

static esp_err_t index_handler(httpd_req_t *req) {
  const char* html = 
    "<html><head><title>ESP32-CAM Entry Gate</title>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<style>"
    "body { font-family: Arial; text-align: center; padding: 20px; background: #0f1115; color: #fff; }"
    "h1 { color: #3a8ef6; }"
    "button { padding: 15px 30px; font-size: 18px; margin: 10px; border: none; border-radius: 8px; cursor: pointer; }"
    ".btn-primary { background: #3a8ef6; color: white; }"
    ".btn-success { background: #28a745; color: white; }"
    "#distance { font-size: 24px; margin: 20px; color: #3a8ef6; }"
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
    "<h1>ESP32-CAM Entry Gate</h1>"
    "<p>Sensor Ultrasonico HC-SR04</p>"
    "<div id='distance'>-- cm</div>"
    "<button class='btn-primary' onclick=\"document.getElementById('img').src='/capture?'+Date.now()\">Atualizar Foto</button><br>"
    "<img id='img' src='/capture' style='max-width: 100%; margin-top: 20px; border-radius: 8px;'><br><br>"
    "<button class='btn-success' onclick=\"fetch('/trigger')\">Enviar para API</button>"
    "</body></html>";
  httpd_resp_send(req, html, strlen(html));
  return ESP_OK;
}

// =================== INICIALIZAR SERVIDOR HTTP ===================
void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  httpd_uri_t index_uri = { .uri = "/", .method = HTTP_GET, .handler = index_handler, .user_ctx = NULL };
  httpd_uri_t capture_uri = { .uri = "/capture", .method = HTTP_GET, .handler = capture_handler, .user_ctx = NULL };
  httpd_uri_t trigger_uri = { .uri = "/trigger", .method = HTTP_GET, .handler = trigger_handler, .user_ctx = NULL };
  httpd_uri_t distance_uri = { .uri = "/distance", .method = HTTP_GET, .handler = distance_handler, .user_ctx = NULL };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    httpd_register_uri_handler(camera_httpd, &trigger_uri);
    httpd_register_uri_handler(camera_httpd, &distance_uri);
    Serial.println("Servidor HTTP iniciado");
  }
}

// =================== SETUP ===================
void setup() {
  Serial.begin(115200);
  Serial.println("\n\nESP32-CAM Entry Gate - Parking System");
  Serial.println("======================================\n");

  // Inicializar servo
  servoBarreira.attach(SERVO_PIN);
  servoBarreira.write(0);

  // Inicializar sensor ultrasonico
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Inicializar LEDs
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  setLeds(true, false);

  // Desligar flash LED
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  // Configuracao da camara
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
  
  if (psramFound()) {
    Serial.println("PSRAM: Disponivel");
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    Serial.println("PSRAM: Nao disponivel");
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Erro na camara: 0x%x\n", err);
    return;
  }
  Serial.println("Camara inicializada");

  // Conectar WiFi
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  startCameraServer();
  Serial.println("\nSistema pronto.");
}

// =================== LOOP ===================
void loop() {
  if (systemBusy) {
    delay(100);
    return;
  }

  long distance = measureDistance();
  static unsigned long lastTriggerTime = 0;
  unsigned long now = millis();

  if (distance > 0 && distance <= DETECTION_DISTANCE && (now - lastTriggerTime) > DEBOUNCE_DELAY) {
    lastTriggerTime = now;
    Serial.printf("Veiculo detectado a %ld cm\n", distance);
    captureAndSend();
  }

  delay(100);
}

// =================== CAPTURA E ENVIO ===================
void captureAndSend() {
  systemBusy = true;
  
  // Liga flash
  digitalWrite(FLASH_LED_PIN, HIGH);
  delay(1000);
  
  camera_fb_t *fb = esp_camera_fb_get();
  
  // Desliga flash
  digitalWrite(FLASH_LED_PIN, LOW);

  if (!fb) {
    Serial.println("Erro na captura");
    systemBusy = false;
    return;
  }
  
  Serial.printf("Foto capturada: %u bytes\n", fb->len);

  WiFiClient client;
  if (client.connect(serverHost, serverPort)) {
    Serial.println("Conectado ao servidor");

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
    
    // Processar resposta
    unsigned long timeout = millis();
    int httpStatusCode = 0;
    String responseBody = "";
    bool headersPassed = false;
    bool barrierOpened = false;
    
    while (client.connected() && millis() - timeout < 10000) {
      if (client.available()) {
        String line = client.readStringUntil('\n');
        
        if (httpStatusCode == 0 && line.startsWith("HTTP/")) {
          int firstSpace = line.indexOf(' ');
          int secondSpace = line.indexOf(' ', firstSpace + 1);
          if (firstSpace > 0 && secondSpace > firstSpace) {
            httpStatusCode = line.substring(firstSpace + 1, secondSpace).toInt();
            Serial.printf("HTTP Status: %d\n", httpStatusCode);
            
            if (httpStatusCode == 200 && !barrierOpened) {
              Serial.println("Acesso autorizado - abrindo barreira");
              setLeds(false, true);
              servoBarreira.write(90);
              barrierOpened = true;
            } else if (httpStatusCode >= 400) {
              Serial.println("Acesso negado");
              setLeds(true, false);
            }
          }
        }
        
        if (line == "\r") {
          headersPassed = true;
        } else if (headersPassed) {
          responseBody += line;
        }
      }
    }
    
    // Processar resultado
    if (httpStatusCode == 200 && barrierOpened) {
      Serial.println("Aguardando veiculo passar...");
      unsigned long startWait = millis();
      unsigned long clearStartTime = 0;
      bool vehiclePassed = false;
      const int CLEAR_CONFIRM_TIME = 2000;
      
      while (millis() - startWait < 30000) {
        long dist = measureDistance();
        
        if (dist > DETECTION_DISTANCE || dist == 0) {
          if (clearStartTime == 0) {
            clearStartTime = millis();
          } else if (millis() - clearStartTime >= CLEAR_CONFIRM_TIME) {
            vehiclePassed = true;
            Serial.println("Veiculo passou");
            break;
          }
        } else {
          clearStartTime = 0;
        }
        delay(100);
      }
      
      if (!vehiclePassed) {
        Serial.println("Timeout - fechando barreira");
      }
      
      delay(3000);
      servoBarreira.write(0);
      setLeds(true, false);
      Serial.println("Barreira fechada");
      
    } else if (httpStatusCode >= 400) {
      bool isDuplicate = (responseBody.indexOf("registo") >= 0 || 
                          responseBody.indexOf("duplic") >= 0 ||
                          responseBody.indexOf("já") >= 0);
      
      if (isDuplicate) {
        Serial.println("Matricula duplicada");
        flashBothLeds(5, 150);
      } else {
        flashBothLeds(3, 150);
      }
      setLeds(true, false);
      
    } else {
      Serial.println("Resposta invalida ou timeout");
    }
    
    client.stop();
  } else {
    Serial.println("Falha na conexao com API");
  }
  
  esp_camera_fb_return(fb);
  systemBusy = false;
}
