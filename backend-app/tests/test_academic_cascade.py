"""Tests for the relational academic selection system."""
import pytest
from app import create_app
from app.extensions import db
from app.models import User
from app.models.academic_structure import (
    School, Department, Trade, SchoolClass, AcademicModule,
)
from app.services.academic_catalog import (
    get_departments, get_trades_by_department, get_levels_by_trade,
    get_classes_by_trade, get_modules_by_trade, get_modules_by_class,
    get_modules_by_department, get_class_context, validate_placement,
    AcademicValidationError,
)
from tests.conftest import TestConfig


class AcademicTestConfig(TestConfig):
    SERVER_NAME = "localhost"


@pytest.fixture
def seeded_app():
    app = create_app(AcademicTestConfig)
    with app.app_context():
        db.create_all()
        school = School(name="Test School", code="TS")
        db.session.add(school)
        db.session.flush()
        dept = Department(school_id=school.id, name="ICT and Multimedia")
        dept2 = Department(school_id=school.id, name="Fashion and Design")
        db.session.add_all([dept, dept2])
        db.session.flush()
        trade = Trade(department_id=dept.id, name="Software Development")
        trade2 = Trade(department_id=dept2.id, name="Fashion Design")
        db.session.add_all([trade, trade2])
        db.session.flush()
        cls = SchoolClass(trade_id=trade.id, name="L3 Software Development", level="L3")
        other = SchoolClass(trade_id=trade2.id, name="L3 Fashion Design", level="L3")
        db.session.add_all([cls, other])
        module = AcademicModule(trade_id=trade.id, level="L3", name="Develop Website", code="SWDWD301")
        db.session.add(module)
        admin = User(username="admin", full_name="Admin", role="master_admin")
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()
        yield app, {"dept": dept, "dept2": dept2, "trade": trade, "trade2": trade2,
                    "class": cls, "class2": other, "module": module, "admin": admin}
        db.drop_all()


@pytest.fixture
def seeded_client(seeded_app):
    app, data = seeded_app
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(data["admin"].id)
    return client, data


def test_departments_filter_trades(seeded_client):
    client, data = seeded_client
    trades = get_trades_by_department(data["dept"].id)
    names = [t.name for t in trades]
    assert names == ["Software Development"]
    assert "Fashion Design" not in names


def test_classes_belong_to_trade_only(seeded_client):
    client, data = seeded_client
    classes = get_classes_by_trade(data["trade"].id)
    assert [c.name for c in classes] == ["L3 Software Development"]
    assert get_classes_by_trade(data["trade2"].id)[0].name == "L3 Fashion Design"


def test_modules_filter_by_trade_and_level(seeded_client):
    client, data = seeded_client
    modules = get_modules_by_trade(data["trade"].id, "L3")
    assert [m.name for m in modules] == ["Develop Website"]
    assert get_modules_by_trade(data["trade"].id, "L5") == []
    # Modules from another trade must never leak in.
    assert get_modules_by_trade(data["trade2"].id) == []


def test_modules_by_class_use_class_level(seeded_client):
    client, data = seeded_client
    modules = get_modules_by_class(data["class"].id)
    assert [m.name for m in modules] == ["Develop Website"]
    assert get_modules_by_class(data["class2"].id) == []


def test_modules_by_department_span_its_trades_only(seeded_client):
    client, data = seeded_client
    modules = get_modules_by_department(data["dept"].id)
    assert [m.name for m in modules] == ["Develop Website"]
    assert get_modules_by_department(data["dept2"].id) == []


def test_class_context_returns_full_chain(seeded_client):
    client, data = seeded_client
    department, trade, klass = get_class_context(data["class"].id)
    assert department.name == "ICT and Multimedia"
    assert trade.name == "Software Development"
    assert klass.name == "L3 Software Development"


def test_validate_placement_rejects_cross_trade_class(seeded_client):
    client, data = seeded_client
    with pytest.raises(AcademicValidationError):
        validate_placement("Software Development", "L3", "L3 Fashion Design")


def test_validate_placement_rejects_cross_level(seeded_client):
    client, data = seeded_client
    with pytest.raises(AcademicValidationError):
        validate_placement("Software Development", "L5", "L3 Software Development")


def test_validate_placement_rejects_unknown_class(seeded_client):
    client, data = seeded_client
    with pytest.raises(AcademicValidationError):
        validate_placement("Software Development", "L3", "Nonexistent Class")


def test_validate_placement_accepts_valid_combination(seeded_client):
    client, data = seeded_client
    department, trade, level, class_name = validate_placement(
        "Software Development", "L3", "L3 Software Development")
    assert department.casefold() == "ict and multimedia"
    assert trade.casefold() == "software development"
    assert level == "L3"
    assert class_name.casefold() == "l3 software development"


def test_api_requires_authentication(seeded_app):
    app, data = seeded_app
    anon = app.test_client()
    response = anon.get("/api/academics/departments")
    assert response.status_code == 302  # redirected to login


def test_api_departments_endpoint(seeded_client):
    client, data = seeded_client
    response = client.get("/api/academics/departments")
    assert response.status_code == 200
    names = {row["name"] for row in response.get_json()}
    assert {"ICT and Multimedia", "Fashion and Design"} <= names


def test_api_trades_scoped_to_department(seeded_client):
    client, data = seeded_client
    response = client.get(f"/api/academics/trades?department_id={data['dept'].id}")
    assert response.status_code == 200
    names = [row["name"] for row in response.get_json()]
    assert names == ["Software Development"]


def test_api_classes_scoped_to_trade(seeded_client):
    client, data = seeded_client
    response = client.get(f"/api/academics/classes?trade_id={data['trade'].id}")
    names = [row["name"] for row in response.get_json()]
    assert names == ["L3 Software Development"]


def test_api_modules_scoped_to_class(seeded_client):
    client, data = seeded_client
    response = client.get(f"/api/academics/modules?class_id={data['class'].id}")
    modules = response.get_json()
    assert [m["name"] for m in modules] == ["Develop Website"]
    assert modules[0]["level"] == "L3"


def test_api_class_context(seeded_client):
    client, data = seeded_client
    response = client.get(f"/api/academics/class-context?class_id={data['class'].id}")
    payload = response.get_json()
    assert payload["department"]["name"] == "ICT and Multimedia"
    assert payload["trade"]["name"] == "Software Development"
    assert payload["class"]["name"] == "L3 Software Development"
    assert payload["modules"][0]["name"] == "Develop Website"


def test_api_structure_nests_everything(seeded_client):
    client, data = seeded_client
    structure = client.get("/api/academics/structure").get_json()
    ict = next(d for d in structure if d["name"] == "ICT and Multimedia")
    sw = next(t for t in ict["trades"] if t["name"] == "Software Development")
    assert "L3 Software Development" in [c["name"] for c in sw["levels"]["L3"]["classes"]]
    assert "Develop Website" in [m["name"] for m in sw["levels"]["L3"]["modules"]]


def test_api_rejects_missing_parent_params(seeded_client):
    client, data = seeded_client
    assert client.get("/api/academics/trades").status_code == 400
    assert client.get("/api/academics/classes").status_code == 400
    assert client.get("/api/academics/modules").status_code == 400
    assert client.get("/api/academics/levels").status_code == 400


def test_api_validate_placement_endpoint(seeded_client):
    client, data = seeded_client
    bad = client.post("/api/academics/validate-placement", json={
        "trade": "Software Development", "level": "L3", "class_name": "L3 Fashion Design"})
    assert bad.status_code == 400
    assert bad.get_json()["valid"] is False
    good = client.post("/api/academics/validate-placement", json={
        "trade": "Software Development", "level": "L3",
        "class_name": "L3 Software Development"})
    assert good.status_code == 200
    assert good.get_json()["department"].casefold() == "ict and multimedia"
