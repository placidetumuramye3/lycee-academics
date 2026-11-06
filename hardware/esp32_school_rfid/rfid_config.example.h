#pragma once

// Copy this file to rfid_config.h and enter the local device credentials.
// rfid_config.h is ignored by Git so Wi-Fi passwords and device tokens do not
// get committed with the firmware.

// ------------------------------------------------------------------ Wi-Fi
const char *WIFI_SSID = "YOUR_WIFI_NAME";
const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ------------------------------------------------------------------ Server
// Address of the Flask app. Use the LAN address of the computer running it
// (it must be on the same network as the ESP32) or the hosted HTTPS address.
//   LAN example:    http://192.168.1.182:5000
//   Hosted example: https://smart-management-school.onrender.com
// Do NOT leave a trailing slash here: the endpoint paths below start with "/".
const char *SERVER_BASE_URL = "http://192.168.1.182:5000";

// true  = HTTPS (hosted app, port 443)
// false = plain HTTP (local/off-network app on port 5000)
const bool SERVER_USE_HTTPS = false;

// Endpoints the firmware calls. The status URL used by the reader is:
//   SERVER_BASE_URL + STATUS_ENDPOINT_PATH  (+ "?class=<RFID_CLASS_NAME>")
// e.g. http://192.168.1.182:5000/student/rfid-status
const char *RFID_ENDPOINT_PATH = "/student/rfid-login";
const char *STATUS_ENDPOINT_PATH = "/student/rfid-status";

// ------------------------------------------------------------------ Device
// Must match RFID_DEVICE_TOKEN in the server's .env.
const char *RFID_DEVICE_TOKEN = "SET_THE_SAME_LONG_RANDOM_TOKEN_IN_RENDER";

// Shown in the server's RFID device logs. Any short stable name works.
const char *RFID_DEVICE_ID = "MAIN_GATE_01";

// Leave empty for cards from all registered classes and school-wide totals.
// Set only if this reader should be restricted to one exact class.
const char *RFID_CLASS_NAME = "";

// ------------------------------------------------------------------ Timing
const unsigned long WIFI_TIMEOUT_MS = 15000; // per Wi-Fi connection attempt
const unsigned long WIFI_RETRY_MS = 10000;   // pause between attempts
const unsigned long IDLE_REFRESH_MS = 30000; // status poll interval

// LCD: 1 = a 16x2 I2C LCD is wired, 0 = LEDs only.
#define LCD_ENABLED 1
