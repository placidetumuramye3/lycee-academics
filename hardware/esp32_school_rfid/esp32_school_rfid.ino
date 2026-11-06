/*
 * ============================================================================
 *  Lycee Academics - ESP32 RFID student attendance reader
 * ============================================================================
 *
 *  What it does
 *  ------------
 *  1. Reads a student's RFID card (MFRC522, 13.56 MHz).
 *  2. Sends the card UID to the Flask app:  POST <SERVER_BASE_URL>/student/rfid-login
 *     with header  X-Device-Token: <RFID_DEVICE_TOKEN>  and body {"uid":"A1B2C3D4"}.
 *     The idle screen polls  GET <SERVER_BASE_URL>/student/rfid-status  every
 *     IDLE_REFRESH_MS; both URLs are built from rfid_config.h.
 *  3. The SERVER decides Present / Late / Absent from its own clock and the
 *     saved Scan Times settings, records the attendance row, and answers.
 *  4. The reader shows the result on three LEDs:
 *
 *        GREEN  = Present  (on time, inside the Present grace window)
 *        YELLOW = Late     (inside the 15-minute late window)
 *        RED    = Absent / denied / unknown card / network error
 *
 *     The LCD (optional) shows the student's name, class and status.
 *
 *  The reader never decides attendance itself - it only displays what the
 *  server returned, so the app stays the single source of truth.
 *
 *  Libraries (Arduino IDE -> Tools -> Manage Libraries)
 *  ----------------------------------------------------
 *    - MFRC522            by GithubCommunity
 *    - ArduinoJson        by Benoit Blanchon (v6 or v7)
 *    - LiquidCrystal I2C  by Frank de Brabander   (only if LCD_ENABLED)
 *    - ESP32 board package by Espressif (Boards Manager URL:
 *      https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json)
 *
 *  Before uploading: copy rfid_config.h.example to rfid_config.h and edit it.
 *  See hardware/README.md for the wiring diagram.
 * ============================================================================
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <time.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

#if __has_include("rfid_config.h")
#include "rfid_config.h"
#else
#error "Missing rfid_config.h - copy rfid_config.h.example to rfid_config.h and fill in your values."
#endif

// Older rfid_config.h files do not define the server/status settings. Fall
// back to the documented local defaults instead of failing to compile.
#ifndef SERVER_BASE_URL
const char *SERVER_BASE_URL = "http://192.168.1.182:5000";
#endif
#ifndef SERVER_USE_HTTPS
const bool SERVER_USE_HTTPS = false;
#endif
#ifndef RFID_ENDPOINT_PATH
const char *RFID_ENDPOINT_PATH = "/student/rfid-login";
#endif
#ifndef STATUS_ENDPOINT_PATH
const char *STATUS_ENDPOINT_PATH = "/student/rfid-status";
#endif
#ifndef RFID_DEVICE_ID
const char *RFID_DEVICE_ID = "MAIN_GATE_01";
#endif
#ifndef RFID_DEVICE_TOKEN
const char *RFID_DEVICE_TOKEN = "";
#endif
#ifndef RFID_CLASS_NAME
const char *RFID_CLASS_NAME = "";
#endif
#ifndef WIFI_TIMEOUT_MS
const unsigned long WIFI_TIMEOUT_MS = 15000;
#endif
#ifndef WIFI_RETRY_MS
const unsigned long WIFI_RETRY_MS = 10000;
#endif
#ifndef IDLE_REFRESH_MS
const unsigned long IDLE_REFRESH_MS = 30000;
#endif
#ifndef LCD_ENABLED
#define LCD_ENABLED 1
#endif

#if LCD_ENABLED
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2); // change 0x27 to 0x3F if the screen stays blank
#endif

// ------------------------------------------------------------------ Pins
// Change these to match your wiring (see hardware/README.md).
#define PIN_RC522_SS 5
#define PIN_RC522_RST 4
#define PIN_LED_GREEN 25
#define PIN_LED_YELLOW 26
#define PIN_LED_RED 27
#define PIN_BUZZER 14 // optional, set to -1 if not fitted

// A define that is not defined (evaluated by #if) counts as 0 and would silently
// disable the buzzer, so give it a real value.
#ifndef PIN_BUZZER
#define PIN_BUZZER -1
#endif

// ------------------------------------------------------------------ State
MFRC522 rfid(PIN_RC522_SS, PIN_RC522_RST);

String lastUid = "";
String statusHint = "";          // last status-poll reason reported by the server
unsigned long lastUidAt = 0;
unsigned long lastIdleRefresh = 0;
unsigned long wifiRetryAt = 0;   // 0 = never attempted yet

// ============================================================================
//  LED helpers
// ============================================================================
void ledsOff()
{
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_RED, LOW);
}

void showLed(int pin)
{
  ledsOff();
  digitalWrite(pin, HIGH);
}

void beep(int times, int onMs, int offMs)
{
#if PIN_BUZZER >= 0
  for (int i = 0; i < times; i++)
  {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(onMs);
    digitalWrite(PIN_BUZZER, LOW);
    if (i < times - 1)
      delay(offMs);
  }
#endif
}

// ============================================================================
//  LCD helpers
// ============================================================================
void lcdLine(uint8_t row, const String &text)
{
#if LCD_ENABLED
  String line = text;
  if (line.length() > 16)
    line = line.substring(0, 16);
  while (line.length() < 16)
    line += ' ';
  lcd.setCursor(0, row);
  lcd.print(line);
#else
  (void)row;
  (void)text;
#endif
}

void lcdShow(const String &top, const String &bottom)
{
  lcdLine(0, top);
  lcdLine(1, bottom);
}

// ============================================================================
//  Wi-Fi
// ============================================================================
bool connectWifi()
{
  if (WiFi.status() == WL_CONNECTED)
    return true;

  // This blocks for up to WIFI_TIMEOUT_MS. loop() runs every 50 ms, so only
  // retry occasionally; otherwise an access point that is down freezes the
  // reader and it never reads cards while reconnecting.
  unsigned long now = millis();
  if (wifiRetryAt != 0 && now - wifiRetryAt < WIFI_RETRY_MS)
    return false;
  wifiRetryAt = now;

  Serial.printf("[wifi] connecting to %s", WIFI_SSID);
  lcdShow("Connecting WiFi", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < WIFI_TIMEOUT_MS)
  {
    delay(500);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.printf("[wifi] connected, IP %s\n", WiFi.localIP().toString().c_str());
    lcdShow("WiFi connected", WiFi.localIP().toString());
    delay(800);
    return true;
  }

  Serial.println("[wifi] FAILED");
  lcdShow("WiFi FAILED", "Check credentials");
  showLed(PIN_LED_RED);
  return false;
}

// ============================================================================
//  HTTP
// ============================================================================
void beginHttp(HTTPClient &http, WiFiClientSecure &secureClient, WiFiClient &plainClient,
               const String &url)
{
  if (SERVER_USE_HTTPS)
  {
    // The school server uses a public certificate, so we do not pin a CA here.
    // For a stricter setup, replace setInsecure() with:
    //   secureClient.setCACert(ROOT_CA_PEM);
    secureClient.setInsecure();
    http.begin(secureClient, url);
  }
  else
  {
    http.begin(plainClient, url);
  }
  http.setTimeout(15000);
  http.setConnectTimeout(10000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", RFID_DEVICE_TOKEN);
  http.addHeader("X-Device-Id", RFID_DEVICE_ID);
}

// Sends one card scan. Returns the HTTP status code (negative = transport error).
int postScan(const String &uid, String &responseBody)
{
  WiFiClientSecure secureClient;
  WiFiClient plainClient;
  HTTPClient http;

  String url = String(SERVER_BASE_URL) + RFID_ENDPOINT_PATH;
  beginHttp(http, secureClient, plainClient, url);

  JsonDocument doc;
  doc["uid"] = uid;
  doc["device_id"] = RFID_DEVICE_ID;
  String payload;
  serializeJson(doc, payload);

  Serial.printf("[scan] POST %s  %s\n", url.c_str(), payload.c_str());
  int code = http.POST(payload);
  responseBody = (code > 0) ? http.getString() : "";
  http.end();

  Serial.printf("[scan] HTTP %d  %s\n", code, responseBody.c_str());
  return code;
}

String urlEncode(const String &value)
{
  static const char hex[] = "0123456789ABCDEF";
  String encoded;
  encoded.reserve(value.length() * 3);
  for (size_t i = 0; i < value.length(); i++)
  {
    char c = value.charAt(i);
    if (isalnum((unsigned char)c) || c == '-' || c == '_' || c == '.' || c == '~')
    {
      encoded += c;
    }
    else
    {
      encoded += '%';
      encoded += hex[(c >> 4) & 0x0F];
      encoded += hex[c & 0x0F];
    }
  }
  return encoded;
}

// Polls the class/school counters for the idle screen.
// Returns the HTTP status code (200 = success, negative = transport error).
int fetchStatus(String &line1, String &line2)
{
  WiFiClientSecure secureClient;
  WiFiClient plainClient;
  HTTPClient http;

  String url = String(SERVER_BASE_URL) + STATUS_ENDPOINT_PATH;
  // Must be a percent-encoded query value ("Class 7A" -> "Class%207A").
  String deviceClass = String(RFID_CLASS_NAME);
  deviceClass.trim();
  if (deviceClass.length() > 0)
  {
    url += "?class=";
    url += urlEncode(deviceClass);
  }
  beginHttp(http, secureClient, plainClient, url);

  Serial.printf("[status] GET %s\n", url.c_str());
  int code = http.GET();
  String body = (code > 0) ? http.getString() : "";
  http.end();
  if (code != 200)
  {
    Serial.printf("[status] HTTP %d  %s\n", code, body.c_str());
    // Show the server's own hint (e.g. reason=server_token_missing) on the LCD
    // so the fix is visible without opening Serial Monitor.
    statusHint = "";
    JsonDocument errDoc;
    if (deserializeJson(errDoc, body) == DeserializationError::Ok)
    {
      String reason = errDoc["reason"] | "";
      if (reason.length())
        statusHint = reason;
    }
    return code == 0 ? -1 : code;
  }

  JsonDocument doc;
  if (deserializeJson(doc, body) != DeserializationError::Ok)
  {
    Serial.printf("[status] invalid JSON: %s\n", body.c_str());
    return -2;
  }

  JsonObject summary = doc["class_summary"];
  if (summary.isNull())
  {
    Serial.printf("[status] missing class_summary: %s\n", body.c_str());
    return -3;
  }

  String name = doc["class_name"] | "All classes";
  line1 = name;
  line2 = "P:" + String((int)(summary["present_count"] | 0)) +
          " L:" + String((int)(summary["late_count"] | 0)) +
          " A:" + String((int)(summary["absent_count"] | 0));
  Serial.printf("[status] %s  %s\n", line1.c_str(), line2.c_str());
  return 200;
}

// ============================================================================
//  Result handling
// ============================================================================
void showResult(const String &uid, int code, const String &body)
{
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, body);
  const char *status = err ? "" : (doc["status"] | "");
  const char *attendance = err ? "" : (doc["attendance_status"] | "");
  String student = err ? "" : String((const char *)(doc["student"] | ""));
  String className = err ? "" : String((const char *)(doc["class_name"] | ""));
  String message = err ? "" : String((const char *)(doc["message"] | ""));

  // ---- Present -----------------------------------------------------------
  if (code == 200 && strcmp(status, "success") == 0 && strcmp(attendance, "Present") == 0)
  {
    showLed(PIN_LED_GREEN);
    beep(1, 120, 0);
    lcdShow(student.length() ? student : "Present", "PRESENT " + className);
    Serial.printf("[result] PRESENT %s\n", student.c_str());
    return;
  }

  // ---- Late --------------------------------------------------------------
  if (code == 200 && strcmp(status, "success") == 0 && strcmp(attendance, "Late") == 0)
  {
    showLed(PIN_LED_YELLOW);
    beep(2, 90, 90);
    lcdShow(student.length() ? student : "Late", "LATE " + className);
    Serial.printf("[result] LATE %s\n", student.c_str());
    return;
  }

  // ---- Afternoon check-in (attendance already decided in the morning) ----
  // The server answers with attendance_status "Absent" and a note such as
  // "attendance remains Absent because the 15-minute morning late-arrival
  // grace period ended", so this must not light green.
  if (code == 200 && strcmp(status, "success") == 0)
  {
    if (strcmp(attendance, "Absent") == 0)
    {
      showLed(PIN_LED_RED);
      beep(3, 250, 120);
      lcdShow(student.length() ? student : "Checked in", "ABSENT - too late");
      Serial.printf("[result] ABSENT (afternoon scan) %s\n", student.c_str());
      return;
    }
    showLed(PIN_LED_GREEN);
    beep(1, 120, 0);
    lcdShow(student.length() ? student : "Checked in", "CHECKED IN " + className);
    Serial.printf("[result] CHECKED IN %s\n", student.c_str());
    return;
  }

  // ---- Meeting check-in --------------------------------------------------
  if (code == 200 && strcmp(status, "meeting_checkin") == 0)
  {
    showLed(PIN_LED_GREEN);
    beep(1, 120, 0);
    lcdShow(student.length() ? student : "Meeting", "MEETING CHECK-IN");
    return;
  }

  // ---- Absent / access denied -------------------------------------------
  if (strcmp(status, "access_denied") == 0)
  {
    showLed(PIN_LED_RED);
    beep(3, 250, 120);
    lcdShow(student.length() ? student : "Access denied", "ABSENT - too late");
    Serial.printf("[result] ABSENT (access denied) %s\n", student.c_str());
    return;
  }

  // ---- Card not registered yet ------------------------------------------
  if (code == 202 && strcmp(status, "pending_registration") == 0)
  {
    showLed(PIN_LED_RED);
    beep(2, 200, 150);
    lcdShow("New card", "Register in app");
    Serial.printf("[result] PENDING REGISTRATION %s\n", uid.c_str());
    return;
  }

  // ---- Lost / inactive / wrong class ------------------------------------
  if (strcmp(status, "lost_card") == 0 || strcmp(status, "student_inactive") == 0 ||
      strcmp(status, "class_not_allowed") == 0 || strcmp(status, "card_not_eligible") == 0)
  {
    showLed(PIN_LED_RED);
    beep(3, 250, 120);
    lcdShow("Card rejected", message.length() ? message : String(status));
    Serial.printf("[result] REJECTED %s\n", status);
    return;
  }

  // ---- Outside the scan windows -----------------------------------------
  if (strcmp(status, "outside_window") == 0)
  {
    showLed(PIN_LED_RED);
    beep(2, 200, 150);
    lcdShow(student.length() ? student : "Outside window", "No scan window");
    return;
  }

  // ---- Device token / server problems -----------------------------------
  if (code == 401)
  {
    showLed(PIN_LED_RED);
    beep(4, 120, 80);
    lcdShow("Device token", "rejected (401)");
    return;
  }
  if (code == 503)
  {
    showLed(PIN_LED_RED);
    beep(2, 200, 150);
    lcdShow("Server busy", "Try again");
    return;
  }

  // ---- Anything else (network error, bad JSON, ...) ---------------------
  showLed(PIN_LED_RED);
  beep(3, 250, 120);
  lcdShow("No connection", code > 0 ? "HTTP " + String(code) : "Network error");
  Serial.printf("[result] UNHANDLED code=%d body=%s\n", code, body.c_str());
}

// ============================================================================
//  Card reading
// ============================================================================
String readCardUid()
{
  if (!rfid.PICC_IsNewCardPresent())
    return "";
  if (!rfid.PICC_ReadCardSerial())
    return "";

  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++)
  {
    if (rfid.uid.uidByte[i] < 0x10)
      uid += '0';
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return uid;
}

void handleCard(const String &uid)
{
  unsigned long now = millis();
  if (uid == lastUid && now - lastUidAt < CARD_DEBOUNCE_MS)
    return; // same tap
  lastUid = uid;
  lastUidAt = now;

  lcdShow("Card " + uid, "Checking...");
  ledsOff();

  if (!connectWifi())
  {
    showResult(uid, -1, "");
    return;
  }

  String body;
  int code = postScan(uid, body);
  showResult(uid, code, body);
}

// ============================================================================
//  Setup / loop
// ============================================================================
void setup()
{
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("Lycee Academics RFID reader starting...");

  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
#if PIN_BUZZER >= 0
  pinMode(PIN_BUZZER, OUTPUT);
#endif
  // A GPIO used as a pin cannot be driven by the disabled-channel trick, so
  // disable the buzzer in rfid_config.h if no buzzer is fitted.
#if PIN_BUZZER >= 0
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
#endif
  ledsOff();

#if LCD_ENABLED
  Wire.begin();
  lcd.init();
  lcd.backlight();
#endif
  lcdShow("Lycee Academics", "Starting...");

  SPI.begin();
  rfid.PCD_Init();
  delay(50);
  byte version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("[rfid] MFRC522 version 0x%02X\n", version);
  if (version == 0x00 || version == 0xFF)
  {
    Serial.println("[rfid] WARNING: reader not detected - check SPI wiring and 3.3V power.");
    lcdShow("Reader missing", "Check wiring");
    showLed(PIN_LED_RED);
  }

  connectWifi();
  syncClock();
  lastIdleRefresh = 0;
  // Counters load on the first loop() pass instead of behind a cold HTTPS handshake.
}

// HTTPS certificate validation needs a correct clock. Plain HTTP is not
// affected, so a failed sync only matters when SERVER_USE_HTTPS is true.
void syncClock()
{
  if (!SERVER_USE_HTTPS || WiFi.status() != WL_CONNECTED)
    return;
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  Serial.print("[time] syncing clock");
  for (int i = 0; i < 20 && time(nullptr) < 1700000000; i++)
  {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
}

void loop()
{
  // Keep the link alive; reconnect quietly if the AP dropped us.
  if (WiFi.status() != WL_CONNECTED)
  {
    connectWifi();
  }

  String uid = readCardUid();
  if (uid.length() > 0)
  {
    handleCard(uid);
    lastIdleRefresh = 0; // refresh counters right after a scan
    return;
  }

  // Idle screen: class/school counters, refreshed periodically.
  if (millis() - lastIdleRefresh > IDLE_REFRESH_MS)
  {
    lastIdleRefresh = millis();
    if (WiFi.status() == WL_CONNECTED)
    {
      String line1, line2;
      int statusCode = fetchStatus(line1, line2);
      if (statusCode == 200)
      {
        lcdShow(line1, line2);
      }
      else
      {
        // Surface why the status poll failed: 401 token mismatch,
        // 503 RFID_DEVICE_TOKEN missing on the server, 403 class mismatch,
        // 404 wrong path/address, <0 Wi-Fi/DNS/TLS problem.
        Serial.printf("[status] sync failed (HTTP %d) via %s %s\n",
                      statusCode, SERVER_BASE_URL, statusHint.c_str());
        lcdShow("Class sync issue", statusHint.length() ? statusHint : "HTTP " + String(statusCode));
      }
    }
    else
    {
      lcdShow("No WiFi", "Tap card to retry");
    }
  }

  delay(50);
}
