"""Check the RFID status endpoint the ESP32 polls.

Run from the backend-app folder on the server that runs the app:

    python check_rfid_status.py

It reads .env exactly like the application (RFID_DEVICE_TOKEN,
RFID_DEVICE_CLASS), calls /student/rfid-status through the Flask test client,
and prints the JSON the reader will receive plus the likely fix.
"""
import os


def main():
    from config import Config
    from app import create_app

    class LocalConfig(Config):
        SERVER_NAME = "localhost"

    token = str(Config.RFID_DEVICE_TOKEN or "")
    device_class = str(Config.RFID_DEVICE_CLASS or "").strip()

    print("RFID_DEVICE_TOKEN :", "<set, %d chars>" % len(token) if token else "MISSING")
    print("RFID_DEVICE_CLASS :", device_class or "<blank: school-wide totals>")
    print("RFID_STATUS_URL   :", Config.RFID_STATUS_URL or
          "<not set; reader builds SERVER_BASE_URL + /student/rfid-status>")
    print("PUBLIC_BASE_URL   :", Config.PUBLIC_BASE_URL or "<not set>")
    print("-" * 60)

    app = create_app(LocalConfig)
    client = app.test_client()
    response = client.get("/student/rfid-status",
                          headers={"X-Device-Token": token} if token else {})
    print("HTTP", response.status_code)
    try:
        print(response.get_json())
    except ValueError:
        print(response.get_data(as_text=True)[:400])

    reason = (response.get_json() or {}).get("reason") if response.is_json else None
    print("-" * 60)
    if response.status_code == 200:
        print("OK: the ESP32 will show the class counters.")
    elif reason == "server_token_missing":
        print("FIX: add RFID_DEVICE_TOKEN to .env (next to config.py), restart the app,")
        print("     and put the SAME value in rfid_config.h (RFID_DEVICE_TOKEN).")
        print("     .env file seen by the app:", os.path.abspath(".env"))
    elif response.status_code == 401:
        print("FIX: the token in rfid_config.h differs from RFID_DEVICE_TOKEN in .env.")
    elif response.status_code == 403:
        print("FIX: RFID_DEVICE_CLASS is set; keep RFID_CLASS_NAME blank in rfid_config.h")
        print("     or set it to exactly this class name.")
    else:
        print("See the JSON message above and the server log.")


if __name__ == "__main__":
    main()
