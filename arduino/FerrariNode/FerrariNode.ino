/*
 * Ferrari IoT — Nó Arduino/ESP32
 * Atua portas, teto, farol, som, motor (relés/servos) e publica telemetria MQTT.
 */
#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP32Servo.h>

const char* WIFI_SSID = "SUA_REDE";
const char* WIFI_PASS = "SUA_SENHA";
const char* MQTT_HOST = "192.168.1.10";
const uint16_t MQTT_PORT = 1883;

#define PIN_SERVO_DOOR  18
#define PIN_SERVO_ROOF  19
#define PIN_HEADLIGHT   26
#define PIN_SOUND       25
#define PIN_ENGINE_RLY  33
#define PIN_LED_STATUS  2

WiFiClient wifi;
PubSubClient mqtt(wifi);
Servo servoDoor, servoRoof;
unsigned long lastHb = 0, lastTel = 0;

void publish(const char* topic, const String& body) { mqtt.publish(topic, body.c_str()); }

void onMessage(char* topic, byte* payload, unsigned int length) {
  String msg; for (unsigned i = 0; i < length; i++) msg += (char)payload[i];
  String t(topic);
  bool on = msg.indexOf("true") >= 0;
  if (t == "ferrari/door") servoDoor.write(on || msg.indexOf("\"open\":true") >= 0 ? 90 : 0);
  else if (t == "ferrari/roof") servoRoof.write(msg.indexOf("true") >= 0 ? 90 : 0);
  else if (t == "ferrari/headlight") digitalWrite(PIN_HEADLIGHT, on ? HIGH : LOW);
  else if (t == "ferrari/sound") digitalWrite(PIN_SOUND, on ? HIGH : LOW);
  else if (t == "ferrari/engine") digitalWrite(PIN_ENGINE_RLY, on ? HIGH : LOW);
}

void ensureMqtt() {
  while (!mqtt.connected()) {
    if (mqtt.connect("arduino-ferrari")) {
      mqtt.subscribe("ferrari/door");
      mqtt.subscribe("ferrari/roof");
      mqtt.subscribe("ferrari/headlight");
      mqtt.subscribe("ferrari/sound");
      mqtt.subscribe("ferrari/engine");
      mqtt.subscribe("ferrari/track");
    } else delay(2000);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_HEADLIGHT, OUTPUT);
  pinMode(PIN_SOUND, OUTPUT);
  pinMode(PIN_ENGINE_RLY, OUTPUT);
  pinMode(PIN_LED_STATUS, OUTPUT);
  servoDoor.attach(PIN_SERVO_DOOR);
  servoRoof.attach(PIN_SERVO_ROOF);
  servoDoor.write(0); servoRoof.write(0);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(400);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  ensureMqtt();
  mqtt.loop();
  unsigned long now = millis();
  if (now - lastTel > 2000) {
    lastTel = now;
    publish("ferrari/rpm", "{\"value\":1200}");
    publish("ferrari/temp", "{\"value\":85.0}");
    publish("ferrari/speed", "{\"value\":0}");
  }
  if (now - lastHb > 1500) {
    lastHb = now;
    publish("ferrari/sync", "{\"board\":\"arduino\",\"ok\":true}");
    digitalWrite(PIN_LED_STATUS, !digitalRead(PIN_LED_STATUS));
  }
}
