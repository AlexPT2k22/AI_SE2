/**
 * ESP32-CAM Parking Monitor - Center Camera
 * 
 * Firmware para a camara central do sistema de estacionamento.
 * Fornece stream MJPEG compativel com OpenCV para detecao de vagas.
 * 
 * Endpoints:
 *   GET /        - Pagina web de status
 *   GET /stream  - Stream MJPEG para OpenCV
 *   GET /capture - Captura de frame unico (JPEG)
 */

#include "Arduino.h"
#include <WiFi.h>
#include "esp_camera.h"
#include <esp_http_server.h>

// =================== CONFIGURACOES DE REDE ===================
const char *ssid = "POCO X3 Pro";
const char *password = "123456789rafael";

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

#define FLASH_LED_PIN      4

httpd_handle_t camera_httpd = NULL;

// =================== HANDLER: STREAM MJPEG ===================
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t *_jpg_buf = NULL;
  char part_buf[128];
  
  static const char* _STREAM_BOUNDARY = "--frameboundary";
  static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=frameboundary");
  if (res != ESP_OK) {
    return res;
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "X-Framerate", "30");
  
  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      res = ESP_FAIL;
      break;
    }
    
    if (fb->format != PIXFORMAT_JPEG) {
      bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
      esp_camera_fb_return(fb);
      fb = NULL;
      if (!jpeg_converted) {
        res = ESP_FAIL;
        break;
      }
    } else {
      _jpg_buf_len = fb->len;
      _jpg_buf = fb->buf;
    }
    
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, "\r\n", 2);
    }
    if (res == ESP_OK) {
      size_t hlen = snprintf(part_buf, sizeof(part_buf), _STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, "\r\n", 2);
    }
    
    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    
    if (res != ESP_OK) {
      break;
    }
    
    delay(33);  // ~30fps
  }
  
  return res;
}

// =================== HANDLER: CAPTURA UNICA ===================
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  
  return res;
}

// =================== HANDLER: PAGINA INICIAL ===================
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
    "<h1>ESP32-CAM Parking Monitor</h1>"
    "<div class='info'>"
    "<p class='status'>Sistema Online</p>"
    "<p>IP: " + WiFi.localIP().toString() + "</p>"
    "<p>Stream MJPEG para OpenCV</p>"
    "</div>"
    "<img src='/stream' id='stream'><br><br>"
    "<div class='info'>"
    "<p><strong>Endpoints:</strong></p>"
    "<p>Stream: <code>http://" + WiFi.localIP().toString() + "/stream</code></p>"
    "<p>Capture: <code>http://" + WiFi.localIP().toString() + "/capture</code></p>"
    "</div>"
    "</body></html>";
  
  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, html.c_str(), html.length());
}

// =================== INICIALIZAR SERVIDOR HTTP ===================
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

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &stream_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    Serial.println("Servidor HTTP iniciado");
    Serial.print("URL: http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Erro ao iniciar servidor HTTP");
  }
}

// =================== SETUP ===================
void setup() {
  Serial.begin(115200);
  Serial.println("\n\nESP32-CAM Parking Monitor - Center Camera");
  Serial.println("==========================================\n");

  // Desligar flash LED
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  // Power-cycle do sensor (resolve problemas de inicializacao)
  pinMode(PWDN_GPIO_NUM, OUTPUT);
  digitalWrite(PWDN_GPIO_NUM, HIGH);
  delay(100);
  digitalWrite(PWDN_GPIO_NUM, LOW);
  delay(100);

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
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  
  // Configuracao baseada na disponibilidade de PSRAM
  if (psramFound()) {
    Serial.println("PSRAM: Disponivel");
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    Serial.println("PSRAM: Nao disponivel");
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  // Inicializar camara com auto-detecao de frequencia XCLK
  esp_err_t err = ESP_FAIL;
  int xclk_freqs[] = {20000000, 10000000, 8000000, 16000000};
  int num_freqs = sizeof(xclk_freqs) / sizeof(xclk_freqs[0]);
  
  Serial.println("Inicializando camara...");
  
  for (int i = 0; i < num_freqs && err != ESP_OK; i++) {
    config.xclk_freq_hz = xclk_freqs[i];
    config.pin_pwdn = PWDN_GPIO_NUM;
    err = esp_camera_init(&config);
    
    if (err != ESP_OK) {
      esp_camera_deinit();
      delay(100);
    }
  }
  
  // Tentar sem PWDN se ainda nao funcionou
  if (err != ESP_OK) {
    config.pin_pwdn = -1;
    for (int i = 0; i < num_freqs && err != ESP_OK; i++) {
      config.xclk_freq_hz = xclk_freqs[i];
      err = esp_camera_init(&config);
      if (err != ESP_OK) {
        esp_camera_deinit();
        delay(100);
      }
    }
  }

  if (err != ESP_OK) {
    Serial.printf("Erro na inicializacao da camara: 0x%x\n", err);
    Serial.println("Verifique a conexao do cabo flat e reinicie.");
    delay(10000);
    ESP.restart();
    return;
  }
  
  Serial.println("Camara inicializada");

  // Configurar sensor
  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_vflip(s, 0);
    s->set_hmirror(s, 0);
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_gain_ctrl(s, 1);
    s->set_agc_gain(s, 0);
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
    s->set_lenc(s, 1);
  }

  // Conectar ao WiFi
  Serial.print("Conectando ao WiFi");
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha na conexao WiFi. Reiniciando...");
    delay(5000);
    ESP.restart();
  }

  startCameraServer();
  
  Serial.println("\nSistema pronto.");
  Serial.print("Stream: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");
}

// =================== LOOP ===================
void loop() {
  // Reconectar WiFi se necessario
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado. Reconectando...");
    WiFi.reconnect();
    delay(5000);
  }
  delay(1000);
}
