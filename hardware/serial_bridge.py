"""Serial bridge for the Arduino Uno / Nano RFID reader.

The Uno has no Wi-Fi, so it prints ``SCAN:<UID>`` on its USB serial port and
waits for a ``RESULT:<STATUS>:<name>:<class>`` line. This script forwards each
scan to the Flask app's ``POST /student/rfid-login`` endpoint and prints the
answer back to the board, which then lights the green / yellow / red LED.

Usage (from the repository root, with the virtual environment active):

    python hardware/serial_bridge.py --port COM3

Configuration comes from the same environment variables the server uses:

    RFID_DEVICE_TOKEN   required, must match the server's .env value
    RFID_DEVICE_CLASS   optional, must match the server's .env value
    PUBLIC_BASE_URL     server base URL, e.g. https://school.example.org
                        (defaults to http://127.0.0.1:5000 for local testing)

Requires ``pyserial``:  pip install pyserial
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - guidance for a missing optional dep
    sys.exit("pyserial is required: pip install pyserial")

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
SCAN_ENDPOINT = "/student/rfid-login"


def _clean(value: str) -> str:
    """Keep the protocol line single-line and colon-free."""
    return str(value or "").replace(":", " ").replace("\r", " ").replace("\n", " ").strip()


def classify(response_code: int, payload: dict) -> str:
    """Map the server answer to PRESENT / LATE / ABSENT / UNKNOWN."""
    status = str(payload.get("status", ""))
    attendance = str(payload.get("attendance_status", ""))
    if response_code == 200 and status == "success":
        if attendance == "Present":
            return "PRESENT"
        if attendance == "Late":
            return "LATE"
        return "PRESENT"  # afternoon / meeting check-in
    if status == "access_denied":
        return "ABSENT"
    if status == "pending_registration":
        return "UNKNOWN"
    return "ABSENT"


def post_scan(base_url: str, token: str, uid: str) -> tuple[int, dict]:
    body = json.dumps({"uid": uid}).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + SCAN_ENDPOINT,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-Device-Token": token},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(raw or "{}")
        except json.JSONDecodeError:
            return error.code, {"message": raw}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return 0, {"message": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge an Arduino RFID reader to the Flask app.")
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM3 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("PUBLIC_BASE_URL", DEFAULT_BASE_URL),
        help="Server base URL (default: PUBLIC_BASE_URL or http://127.0.0.1:5000)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("RFID_DEVICE_TOKEN", ""),
        help="Device token (default: RFID_DEVICE_TOKEN)",
    )
    args = parser.parse_args()

    if not args.token:
        print("Warning: no device token set. The server will reject scans if RFID_DEVICE_TOKEN is configured.")

    print(f"Opening {args.port} at {args.baud} baud -> {args.base_url}")
    with serial.Serial(args.port, args.baud, timeout=1) as board:
        time.sleep(2)  # the Uno resets when the port opens
        board.reset_input_buffer()
        print("Bridge ready. Tap a card.")

        while True:
            raw = board.readline().decode("utf-8", "replace").strip()
            if not raw:
                continue
            if not raw.startswith("SCAN:"):
                print(f"[board] {raw}")
                continue

            uid = raw[5:].strip().upper()
            code, payload = post_scan(args.base_url, args.token, uid)
            status = classify(code, payload)
            name = _clean(payload.get("student", ""))
            class_name = _clean(payload.get("class_name", ""))
            if not name:
                name = uid
            if not class_name:
                class_name = _clean(payload.get("message", ""))[:40] or "-"

            line = f"RESULT:{status}:{name}:{class_name}"
            board.write((line + "\n").encode("utf-8"))
            print(f"[scan] {uid} -> HTTP {code} {status} {name} ({class_name})")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nBridge stopped.")
