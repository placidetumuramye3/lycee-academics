"""The RFID status endpoint the ESP32 polls, and the URL it is configured with."""
import pytest
from app import create_app
from app.extensions import db
from app.models import User
from app.models.academic_structure import School, Department, Trade, SchoolClass
from tests.conftest import TestConfig

TOKEN = "test-device-token"


class RfidTestConfig(TestConfig):
    SERVER_NAME = "localhost"
    RFID_DEVICE_TOKEN = TOKEN
    RFID_DEVICE_CLASS = ""
    PUBLIC_BASE_URL = ""


@pytest.fixture
def rfid_app():
    app = create_app(RfidTestConfig)
    with app.app_context():
        db.create_all()
        school = School(name="RFID School", code="RF")
        db.session.add(school)
        db.session.flush()
        dept = Department(school_id=school.id, name="ICT and Multimedia")
        db.session.add(dept)
        db.session.flush()
        trade = Trade(department_id=dept.id, name="Software Development")
        db.session.add(trade)
        db.session.flush()
        student = User(username="learner", full_name="Learner", role="student")
        student.set_password("password123")
        db.session.add_all([
            student,
            SchoolClass(trade_id=trade.id, name="L3 SOFTWARE DEVELOPMENT", level="L3"),
        ])
        db.session.commit()
        yield app
        db.drop_all()


def test_status_url_returns_the_counters_shape_the_firmware_parses(rfid_app):
    client = rfid_app.test_client()
    response = client.get("/student/rfid-status", headers={"X-Device-Token": TOKEN})
    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["class_name"]
    # fetchStatus() reads class_summary.present_count / late_count / absent_count
    assert {"present_count", "late_count", "absent_count"} <= set(payload["class_summary"])


def test_status_url_requires_the_device_token(rfid_app):
    client = rfid_app.test_client()
    assert client.get("/student/rfid-status").status_code == 401
    assert client.get("/student/rfid-status",
                      headers={"X-Device-Token": "wrong"}).status_code == 401


def test_status_url_with_a_leading_space_path_explains_the_fix(rfid_app):
    client = rfid_app.test_client()
    response = client.get("/%20student/rfid-status", headers={"X-Device-Token": TOKEN})
    assert response.status_code == 404
    message = response.get_json()["message"]
    assert "/student/rfid-status" in message
    assert "space" in message


def test_missing_server_token_is_reported_clearly(rfid_app):
    rfid_app.config["RFID_DEVICE_TOKEN"] = ""
    client = rfid_app.test_client()
    response = client.get("/student/rfid-status")
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["reason"] == "server_token_missing"
    assert "RFID_DEVICE_TOKEN" in payload["message"]


def test_reconciliation_failure_still_returns_counters(rfid_app, monkeypatch):
    def boom(now=None):
        raise RuntimeError("database busy")

    monkeypatch.setattr("app.routes.rfid.reconcile_daily_absences", boom)
    client = rfid_app.test_client()
    response = client.get("/student/rfid-status", headers={"X-Device-Token": TOKEN})
    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["class_summary"]["present_count"] == 0
    assert payload["absences_recorded"] == 0


def test_scanner_page_shows_the_configured_status_url(rfid_app):
    client = rfid_app.test_client()
    html = client.get("/student/rfid-login").get_data(as_text=True)
    assert "/student/rfid-status" in html
    assert "SERVER_BASE_URL + STATUS_ENDPOINT_PATH" in html

    rfid_app.config["RFID_STATUS_URL"] = "http://192.168.1.182:5000/student/rfid-status"
    html = client.get("/student/rfid-login").get_data(as_text=True)
    assert "http://192.168.1.182:5000/student/rfid-status" in html
