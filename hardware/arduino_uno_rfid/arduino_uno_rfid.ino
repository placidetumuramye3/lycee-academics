/*
 * ============================================================================
 *  Lycee Academics - Arduino Uno / Nano RFID reader (serial bridge)
 * ============================================================================
 *
 *  The Uno has no Wi-Fi, so it does not talk to the server directly.
 *  It reads the card and prints one line on the USB serial port:
 *
 *        SCAN:A1B2C3D4
 *
 *  A small Python bridge on the PC (hardware/serial_bridge.py) forwards that
 *  line to POST /student/rfid-login and prints the answer back:
 *
 *        RESULT:PRESENT:Jean Bosco:Class 7A
 *        RESULT:LATE:Jean Bosco:Class 7A
 *        RESULT:ABSENT:Jean Bosco:Class 7A
 *        RESULT:UNKNOWN:A1B2C3D4
 *
 *  The Uno then lights the matching LED:
 *        GREEN  = Present
 *        YELLOW = Late
 *        RED    = Absent / unknown card / bridge not running
 *
 *  Libraries: MFRC522 by GithubCommunity
 *  Board:     Arduino Uno (or Nano), 9600 baud
 * ============================================================================
 */

#include <SPI.h>
#include <MFRC522.h>

// ------------------------------------------------------------------ Pins
#define PIN_RC522_SS 10
#define PIN_RC522_RST 9
#define PIN_LED_GREEN 5
#define PIN_LED_YELLOW 6
#define PIN_LED_RED 7
#define PIN_BUZZER 8 // optional, set to -1 if not fitted

#define CARD_DEBOUNCE_MS 3000UL
#define RESULT_TIMEOUT_MS 20000UL // how long to wait for the bridge's answer

MFRC522 rfid(PIN_RC522_SS, PIN_RC522_RST);

String lastUid = "";
unsigned long lastUidAt = 0;

// ============================================================================
//  LEDs / buzzer
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

// ============================================================================
//  Bridge protocol
// ============================================================================
void sendScan(const String &uid)
{
  Serial.print("SCAN:");
  Serial.println(uid);
}

// Waits for "RESULT:<STATUS>:<name>:<class>" and lights the LED.
void waitForResult()
{
  unsigned long started = millis();
  String line = "";

  while (millis() - started < RESULT_TIMEOUT_MS)
  {
    while (Serial.available())
    {
      char c = (char)Serial.read();
      if (c == '\n')
      {
        line.trim();
        if (line.startsWith("RESULT:"))
        {
          // Split into at most 4 parts: RESULT, STATUS, name, class
          String parts[4];
          int count = 0;
          int start = 0;
          for (int i = 0; i <= (int)line.length() && count < 4; i++)
          {
            if (i == (int)line.length() || line.charAt(i) == ':')
            {
              parts[count++] = line.substring(start, i);
              start = i + 1;
            }
          }
          String status = (count > 1) ? parts[1] : "";

          if (status == "PRESENT")
          {
            showLed(PIN_LED_GREEN);
            beep(1, 120, 0);
          }
          else if (status == "LATE")
          {
            showLed(PIN_LED_YELLOW);
            beep(2, 90, 90);
          }
          else
          {
            showLed(PIN_LED_RED);
            beep(3, 250, 120);
          }
          return;
        }
        line = "";
      }
      else if (c != '\r')
      {
        line += c;
      }
    }
  }

  // No answer from the bridge: treat as not recorded.
  showLed(PIN_LED_RED);
  beep(3, 250, 120);
}

// ============================================================================
//  Setup / loop
// ============================================================================
void setup()
{
  Serial.begin(9600);
  delay(300);

  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
#if PIN_BUZZER >= 0
  pinMode(PIN_BUZZER, OUTPUT);
#endif
  ledsOff();

  SPI.begin();
  rfid.PCD_Init();
  delay(50);

  Serial.println("READY");
  // Quick self-test: all three LEDs in sequence.
  showLed(PIN_LED_GREEN);
  delay(250);
  showLed(PIN_LED_YELLOW);
  delay(250);
  showLed(PIN_LED_RED);
  delay(250);
  ledsOff();
}

void loop()
{
  String uid = readCardUid();
  if (uid.length() == 0)
  {
    delay(50);
    return;
  }

  unsigned long now = millis();
  if (uid == lastUid && now - lastUidAt < CARD_DEBOUNCE_MS)
    return;
  lastUid = uid;
  lastUidAt = now;

  ledsOff();
  sendScan(uid);
  waitForResult();
}
