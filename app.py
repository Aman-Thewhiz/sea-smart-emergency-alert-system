import os
import sqlite3
import threading
import time
import uuid
import logging
import re
from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib

from flask import Flask, jsonify, render_template, request, g

from dotenv import load_dotenv

try:
    import phonenumbers
except ImportError:
    phonenumbers = None

try:
    from twilio.rest import Client
except ImportError:
    Client = None

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "alerts.db")

app = Flask(__name__)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_format = "%(asctime)s %(levelname)s request_id=%(request_id)s %(message)s"
_record_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    record = _record_factory(*args, **kwargs)
    if not hasattr(record, "request_id"):
        record.request_id = "-"
    return record


logging.setLogRecordFactory(record_factory)
logging.basicConfig(level=log_level, format=log_format)

logger = logging.getLogger("sea")
logger.addFilter(RequestIdFilter())

log_file = os.getenv("LOG_FILE")
if log_file:
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.addFilter(RequestIdFilter())
    logger.addHandler(file_handler)

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "5"))
_rate_limit_store = {}
_rate_limit_lock = threading.Lock()
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "IN").upper()
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


def init_db() -> None:
    # Ensure the alerts table exists before serving requests.
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude TEXT NOT NULL,
                longitude TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude TEXT NOT NULL,
                longitude TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


init_db()


@app.errorhandler(Exception)
def handle_exception(error):
    print("GLOBAL ERROR:", str(error))
    return (
        jsonify(
            {
                "success": False,
                "message": "Internal server error",
                "error": str(error),
            }
        ),
        500,
    )


@app.before_request
def assign_request_id():
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    g.request_id = request_id


@app.after_request
def add_request_id_header(response):
    response.headers["X-Request-ID"] = g.get("request_id", "")
    return response


def log_event(message: str) -> None:
    logger.info(message, extra={"request_id": g.get("request_id", "-")})


def send_email_alert(to_email: str, latitude: str, longitude: str, timestamp: str) -> bool:
    if DEMO_MODE:
        print("[DEMO MODE] Email simulated:", to_email)
        return True

    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        mail_from = os.getenv("EMERGENCY_EMAIL_FROM")

        if not smtp_host or not smtp_user or not smtp_pass or not mail_from:
            raise Exception("SMTP not configured")

        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"

        msg = EmailMessage()
        msg["Subject"] = "Emergency Alert"
        msg["From"] = mail_from
        msg["To"] = to_email
        msg.set_content(f"Emergency! Location: {maps_link}")

        with smtplib.SMTP(smtp_host, 587) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return True
    except Exception as exc:
        print("Email failed:", str(exc))
        return False


def send_sms_alert(to_phone: str, latitude: str, longitude: str, timestamp: str) -> bool:
    if DEMO_MODE:
        print("[DEMO MODE] SMS simulated:", to_phone)
        return True

    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not account_sid or not auth_token or not from_number:
            raise Exception("Twilio not configured")

        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"

        client = Client(account_sid, auth_token)

        client.messages.create(
            body=f"Emergency! Location: {maps_link}",
            from_=from_number,
            to=to_phone,
        )

        return True
    except Exception as exc:
        print("SMS failed:", str(exc))
        return False


def insert_alert(latitude: str, longitude: str, timestamp: str) -> int:
    # Persist the alert so it appears in history dashboards.
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alerts (latitude, longitude, timestamp) VALUES (?, ?, ?)",
            (latitude, longitude, timestamp),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def fetch_alerts():
    # Load all alerts for the dashboard and history page.
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, latitude, longitude, timestamp FROM alerts ORDER BY id DESC"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def insert_tracking(latitude: str, longitude: str, timestamp: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tracking (latitude, longitude, timestamp) VALUES (?, ?, ?)",
            (latitude, longitude, timestamp),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def fetch_latest_tracking():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, latitude, longitude, timestamp FROM tracking ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_tracking_history():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, latitude, longitude, timestamp FROM tracking ORDER BY id DESC"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/alerts", methods=["GET"])
def alerts():
    return jsonify({"alerts": fetch_alerts()})


@app.route("/get_alerts", methods=["GET"])
def get_alerts():
    return jsonify({"alerts": fetch_alerts()})


@app.route("/add_contact", methods=["POST"])
def add_contact():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()

    if not name:
        return jsonify({"success": False, "message": "Name required"}), 400

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO contacts (name, email, phone, created_at) VALUES (?, ?, ?, ?)",
            (name, email or None, phone or None, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True})


@app.route("/get_contacts", methods=["GET"])
def get_contacts():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM contacts ORDER BY id DESC").fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()


@app.route("/update_location", methods=["POST"])
def update_location():
    data = request.get_json(silent=True) or {}
    latitude = str(data.get("latitude", "")).strip()
    longitude = str(data.get("longitude", "")).strip()

    if not latitude or not longitude:
        return jsonify({"success": False, "message": "Missing coordinates."}), 400

    try:
        lat_value = parse_coordinate(latitude, "latitude", -90, 90)
        lng_value = parse_coordinate(longitude, "longitude", -180, 180)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    timestamp = datetime.now(timezone.utc).isoformat()
    tracking_id = insert_tracking(f"{lat_value:.6f}", f"{lng_value:.6f}", timestamp)

    return jsonify(
        {
            "success": True,
            "tracking": {
                "id": tracking_id,
                "latitude": f"{lat_value:.6f}",
                "longitude": f"{lng_value:.6f}",
                "timestamp": timestamp,
            },
        }
    )


@app.route("/get_live_location", methods=["GET"])
def get_live_location():
    return jsonify({"success": True, "location": fetch_latest_tracking()})


@app.route("/get_tracking_history", methods=["GET"])
def get_tracking_history():
    return jsonify({"success": True, "locations": fetch_tracking_history()})


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.Error:
        return jsonify({"status": "error"}), 500
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


def get_client_id() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def is_rate_limited(client_id: str) -> bool:
    now = time.time()
    with _rate_limit_lock:
        history = _rate_limit_store.get(client_id, [])
        history = [ts for ts in history if now - ts < RATE_LIMIT_WINDOW_SECONDS]
        if len(history) >= RATE_LIMIT_MAX:
            _rate_limit_store[client_id] = history
            return True
        history.append(now)
        _rate_limit_store[client_id] = history
        return False


def parse_coordinate(value: str, name: str, min_value: float, max_value: float) -> float:
    try:
        numeric = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {name} coordinate.") from exc
    if not (min_value <= numeric <= max_value):
        raise ValueError(f"{name.capitalize()} out of range.")
    return numeric


def validate_email(value: str) -> None:
    if not EMAIL_REGEX.match(value):
        raise ValueError("Invalid contact email.")


def normalize_phone(value: str) -> str:
    if phonenumbers is None:
        raise RuntimeError("Missing phone dependency. Install phonenumbers.")

    try:
        parsed = phonenumbers.parse(value, DEFAULT_COUNTRY)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Invalid contact phone.") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid contact phone.")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


@app.route("/send_alert", methods=["POST"])
def send_alert():
    try:
        data = request.get_json(silent=True) or {}

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if not latitude or not longitude:
            return jsonify({"success": False, "message": "Missing location"}), 400

        timestamp = datetime.now(timezone.utc).isoformat()
        alert_id = insert_alert(latitude, longitude, timestamp)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        contacts = conn.execute("SELECT * FROM contacts").fetchall()
        conn.close()

        results = []

        for contact in contacts:
            email_status = False
            sms_status = False

            if contact["email"]:
                email_status = send_email_alert(
                    contact["email"],
                    latitude,
                    longitude,
                    timestamp,
                )

            if contact["phone"]:
                sms_status = send_sms_alert(
                    contact["phone"],
                    latitude,
                    longitude,
                    timestamp,
                )

            results.append(
                {
                    "name": contact["name"],
                    "email_sent": email_status,
                    "sms_sent": sms_status,
                }
            )

        return jsonify(
            {
                "success": True,
                "message": f"Alert sent to {len(results)} contacts",
                "delivery_results": results,
                "alert_id": alert_id,
            }
        )

    except Exception as exc:
        print("Send alert error:", str(exc))
        return jsonify({"success": False, "error": str(exc)})


if __name__ == "__main__":
    init_db()
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
