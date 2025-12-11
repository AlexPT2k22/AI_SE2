#include "Arduino.h"
#include <WiFi.h>
#include "esp_camera.h"
#include <esp_http_server.h>

// =================== CONFIGURAÇÕES ===================
const char *ssid = "POCO X3 Pro";
const char *password = "123456789rafael";

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

// =================== STREAM MJPEG MELHORADO PARA OPENCV ===================
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char part_buf[128];
  
  // Define boundary compatível com OpenCV
  static const char* _STREAM_BOUNDARY = "--frameboundary";
  static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

  // Headers MJPEG
  res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=frameboundary");
  if(res != ESP_OK){
    Serial.println("Erro ao definir tipo de resposta");
    return res;
  }

  // Adiciona headers para compatibilidade
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "X-Framerate", "30");
  
  Serial.println("Cliente conectado ao stream");
  
  while(true){
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Falha na captura do frame");
      res = ESP_FAIL;
      break;
    }
    
    // Garante que está em JPEG
    if(fb->format != PIXFORMAT_JPEG){
      bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
      esp_camera_fb_return(fb);
      fb = NULL;
      if(!jpeg_converted){
        Serial.println("Falha na conversão JPEG");
        res = ESP_FAIL;
        break;
      }
    } else {
      _jpg_buf_len = fb->len;
      _jpg_buf = fb->buf;
    }
    
    // Envia boundary
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, "\r\n", 2);
    }
    
    // Envia headers do frame
    if(res == ESP_OK){
      size_t hlen = snprintf(part_buf, sizeof(part_buf), _STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    
    // Envia o frame JPEG
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    
    // Envia finalizador
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, "\r\n", 2);
    }
    
    // Libera o framebuffer
    if(fb){
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf){
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    
    if(res != ESP_OK){
      Serial.println("Cliente desconectado");
      break;
    }
    
    // Pequeno delay para não sobrecarregar (30fps)
    delay(33);
  }
  
  return res;
}

// Handler para captura única
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Falha na captura");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  
  Serial.println("Frame único capturado");
  return res;
}

// Página inicial
static esp_err_t index_handler(httpd_req_t *req) {
  String html = 
    "<html><head><title>ESP32-CAM Parking Monitor</title>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<style>"
    "body { font-family: Arial; text-align: center; padding: 20px; background: #1a1a1a; color: #fff; }"
    "h1 { color: #4CAF50; }"
    "img { max-width: 100%; border: 3px solid #4CAF50; border-radius: 8px; }"
    ".info { background: #333; padding: 15px; border-radius: 8px; margin: 20px auto; max-width: 600px; }"
    ".status { color: #4CAF50; font-weight: bold; }"
    "</style></head><body>"
    "<h1>🅿️ ESP32-CAM Parking Monitor</h1>"
    "<div class='info'>"
    "<p class='status'>✓ Sistema Online</p>"
    "<p>IP: " + WiFi.localIP().toString() + "</p>"
    "<p>Stream MJPEG otimizado para OpenCV</p>"
    "</div>"
    "<img src='/stream' id='stream'><br><br>"
    "<div class='info'>"
    "<p><strong>Endpoints disponíveis:</strong></p>"
    "<p>Stream: <code>http://" + WiFi.localIP().toString() + "/stream</code></p>"
    "<p>Capture: <code>http://" + WiFi.localIP().toString() + "/capture</code></p>"
    "</div>"
    "<script>"
    "document.getElementById('stream').onerror = function() {"
    "  console.error('Erro ao carregar stream');"
    "};"
    "</script>"
    "</body></html>";
  
  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, html.c_str(), html.length());
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_uri_handlers = 8;
  config.ctrl_port = 32768;
  config.max_open_sockets = 7;
  config.recv_wait_timeout = 10;
  config.send_wait_timeout = 10;

  httpd_uri_t index_uri = {
    .uri       = "/",
    .method    = HTTP_GET,
    .handler   = index_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t capture_uri = {
    .uri       = "/capture",
    .method    = HTTP_GET,
    .handler   = capture_handler,
    .user_ctx  = NULL
  };

  Serial.println("Iniciando servidor HTTP...");
  
  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &stream_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    Serial.println("✓ Servidor HTTP iniciado!");
    Serial.print("  Página: http://");
    Serial.println(WiFi.localIP());
    Serial.print("  Stream: http://");
    Serial.print(WiFi.localIP());
    Serial.println("/stream");
  } else {
    Serial.println("✗ ERRO ao iniciar servidor HTTP!");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n╔════════════════════════════════════╗");
  Serial.println("║  ESP32-CAM Parking Monitor v2.0   ║");
  Serial.println("║  OpenCV-Compatible MJPEG Stream   ║");
  Serial.println("╚════════════════════════════════════╝\n");

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
  
  if(psramFound()){
    Serial.println("✓ PSRAM encontrada - Usando alta qualidade");
    config.frame_size = FRAMESIZE_VGA; // 640x480 - melhor para ALPR
    config.jpeg_quality = 12; // 10-63 (menor = melhor qualidade)
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    Serial.println("⚠ PSRAM não encontrada - Modo básico");
    config.frame_size = FRAMESIZE_QVGA; // 320x240
    config.jpeg_quality = 15;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  Serial.print("Inicializando câmara...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("\n✗ FALHA! Erro: 0x%x\n", err);
    Serial.println("Reiniciando em 5 segundos...");
    delay(5000);
    ESP.restart();
    return;
  }
  Serial.println(" OK!");

  // Ajustes do sensor para melhor qualidade
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_vflip(s, 0);        // Espelha verticalmente
    s->set_hmirror(s, 0);      // Espelha horizontalmente
    s->set_brightness(s, 0);   // -2 a 2
    s->set_contrast(s, 0);     // -2 a 2
    s->set_saturation(s, 0);   // -2 a 2
    s->set_whitebal(s, 1);     // White balance automático
    s->set_awb_gain(s, 1);     // Auto white balance gain
    s->set_wb_mode(s, 0);      // White balance mode
    s->set_exposure_ctrl(s, 1);// Auto exposure
    s->set_aec2(s, 0);         // AEC DSP
    s->set_gain_ctrl(s, 1);    // Auto gain
    s->set_agc_gain(s, 0);     // AGC gain
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);          // Black pixel correction
    s->set_wpc(s, 1);          // White pixel correction
    s->set_raw_gma(s, 1);      // Gamma
    s->set_lenc(s, 1);         // Lens correction
    Serial.println("✓ Sensor configurado!");
  }

  Serial.print("\nConectando ao WiFi ");
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if(WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi conectado!");
    Serial.print("   SSID: ");
    Serial.println(ssid);
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("   Signal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\n✗ Falha ao conectar WiFi!");
    Serial.println("Reiniciando em 5 segundos...");
    delay(5000);
    ESP.restart();
  }

  startCameraServer();
  
  Serial.println("\n╔════════════════════════════════════╗");
  Serial.println("║         SISTEMA PRONTO!            ║");
  Serial.println("╚════════════════════════════════════╝");
  Serial.print("\n🌐 Acesse: http://");
  Serial.println(WiFi.localIP());
  Serial.println("\n✓ Aguardando conexões...\n");
}

void loop() {
  // Verifica conexão WiFi
  if(WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi desconectado! Reconectando...");
    WiFi.reconnect();
    delay(5000);
  }
  delay(1000);
}
