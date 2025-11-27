#include "Arduino.h"
#include <WiFi.h>
#include "esp_camera.h"
#include <esp_http_server.h>

// =================== CONFIGURAÇÕES ===================
const char *ssid = "Tenda_1F8C60";
const char *password = "j35Cm7U4c6";

// Configurações do Servidor API
const char* serverHost = "192.168.68.125";
const int serverPort = 8000;
const char* serverPath = "/api/entry";
const char* cameraId = "gate-entrada";

#define TRIGGER_PIN 13 

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

// Página inicial simples
static esp_err_t index_handler(httpd_req_t *req) {
  const char* html = 
    "<html><head><title>ESP32-CAM Gate</title>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "</head><body style='font-family: Arial; text-align: center; padding: 20px;'>"
    "<h1>Gate Camera (OV3660)</h1>"
    "<p>Modo Simples - Sem Stream Cont&iacute;nuo</p>"
    "<button onclick=\"document.getElementById('img').src='/capture?'+Date.now()\" "
    "style='padding: 15px 30px; font-size: 18px; margin: 10px;'>Atualizar Foto</button><br>"
    "<img id='img' src='/capture' style='max-width: 100%; margin-top: 20px;'><br><br>"
    "<button onclick=\"fetch('/trigger')\" "
    "style='padding: 15px 30px; font-size: 18px; background: green; color: white;'>"
    "Enviar para API</button>"
    "</body></html>";
  httpd_resp_send(req, html, strlen(html));
  return ESP_OK;
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

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    httpd_register_uri_handler(camera_httpd, &trigger_uri);
    Serial.println("Servidor HTTP iniciado!");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=== ESP32-CAM OV3660 - Modo Simples ===");

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
  config.grab_mode = CAMERA_GRAB_LATEST; // Sempre pega o frame mais recente
  
  // Configuração conservadora
  if(psramFound()){
    Serial.println("PSRAM encontrada!");
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 12;
    config.fb_count = 1; // Apenas 1 buffer para evitar FB-OVF
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

  // Corrigir orientação da imagem
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_vflip(s, 1);  // Flip vertical (imagem de cabeça para baixo)
    s->set_hmirror(s, 1); // Espelho horizontal (se necessário)
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
  pinMode(TRIGGER_PIN, INPUT_PULLUP);
  
  Serial.println("=== PRONTO! ===");
}

void loop() {
  if (digitalRead(TRIGGER_PIN) == LOW) {
    Serial.println("Gatilho fisico!");
    captureAndSend();
    delay(5000);
  }
  delay(100);
}

void captureAndSend() {
  camera_fb_t * fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("Falha na captura");
    return;
  }

  Serial.printf("Foto: %u bytes\n", fb->len);

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
    
    unsigned long timeout = millis();
    while (client.connected() && millis() - timeout < 10000) {
      if (client.available()) {
        String line = client.readStringUntil('\n');
        if (line == "\r") {
          Serial.println("Resposta:");
          Serial.println(client.readString());
          break;
        }
      }
    }
    client.stop();
  } else {
    Serial.println("Falha ao conectar na API");
  }
  
  esp_camera_fb_return(fb);
}
