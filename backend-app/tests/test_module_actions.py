"""Module maintenance (add / edit / remove) and relational department lists."""
import pytest
from app import create_app
from app.extensions import db
from app.models import User
from app.models.academic_structure import (
    School, Department, Trade, SchoolClass, AcademicModule,
)
from app.services.academic_catalog import (
    AcademicValidationError, create_module, update_module, delete_module,
)
from tests.conftest import TestConfig


class ModuleTestConfig(TestConfig):
    SERVER_NAME = "localhost"


REQUESTED_DEPARTMENTS = [
    "ICT and Multimedia", "Fashion and Design", "Accounting",
]


@pytest.fixture
def module_app():
    app = create_app(ModuleTestConfig)
    with app.app_context():
        db.create_all()
        school = School(name="Module School", code="MS")
        db.session.add(school)
        db.session.flush()
        ict = Department(school_id=school.id, name="ICT and Multimedia")
        db.session.add(ict)
        db.session.flush()
        swd = Trade(department_id=ict.id, name="Software Development")
        nit = Trade(department_id=ict.id, name="Networking and Internet Technology")
        db.session.add_all([swd, nit])
        db.session.flush()
        l3 = SchoolClass(trade_id=swd.id, name="L3 Software Development", level="L3")
        l4 = SchoolClass(trade_id=swd.id, name="L4 Software Development", level="L4")
        db.session.add_all([l3, l4])
        for name, trade_name in (("Fashion and Design", "Fashion and Design"),
                                 ("Accounting", "Accounting")):
            department = Department(school_id=school.id, name=name)
            db.session.add(department)
            db.session.flush()
            db.session.add(Trade(department_id=department.id, name=trade_name))
        admin = User(username="admin", full_name="Admin", role="master_admin")
        admin.set_password("password123")
        student = User(username="learner", full_name="Learner", role="student")
        student.set_password("password123")
        db.session.add_all([admin, student])
        db.session.commit()
        yield app, {"ict": ict, "swd": swd, "nit": nit, "l3": l3, "l4": l4,
                    "admin": admin, "student": student}
        db.drop_all()


def _client(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
    return client


@pytest.fixture
def admin_client(module_app):
    app, data = module_app
    return _client(app, data["admin"]), data


@pytest.fixture
def student_client(module_app):
    app, data = module_app
    return _client(app, data["student"]), data


def test_department_list_contains_the_requested_departments(admin_client):
    client, _ = admin_client
    names = [row["name"] for row in client.get("/api/academics/departments").get_json()]
    assert sorted(names) == sorted(REQUESTED_DEPARTMENTS)
    # The transcribed catalog uses exactly the same department vocabulary.
    from app.data.module_catalog import DEPARTMENTS
    assert {department["name"] for department in DEPARTMENTS} == set(REQUESTED_DEPARTMENTS)


def test_add_module_with_hours_periods_and_weight(admin_client):
    client, data = admin_client
    response = client.post("/api/academics/modules", json={
        "name": "Develop Website", "code": "SWDWD301",
        "hours": 110, "periods": 165, "weight": 3,
        "category": "Specific", "department_id": data["ict"].id,
        "trade_id": data["swd"].id, "level": "L3", "class_id": data["l3"].id,
    })
    assert response.status_code == 201, response.get_json()
    payload = response.get_json()["module"]
    assert payload["name"] == "Develop Website"
    assert payload["code"] == "SWDWD301"
    assert payload["hours"] == 110
    assert payload["periods"] == 165
    assert payload["weight"] == 3
    assert payload["trade"] == "Software Development"
    assert payload["department"] == "ICT and Multimedia"
    # The class inherits the module of its level.
    listed = client.get("/api/academics/modules?class_id=%d" % data["l3"].id).get_json()
    assert [m["name"] for m in listed] == ["Develop Website"]


def test_periods_default_to_one_and_a_half_times_hours(admin_client):
    client, data = admin_client
    response = client.post("/api/academics/modules", json={
        "name": "Apply Algebra", "code": "GENAT302", "hours": 60,
        "department_id": data["ict"].id, "trade_id": data["swd"].id, "level": "L3",
    })
    assert response.status_code == 201
    module = response.get_json()["module"]
    assert module["periods"] == 90
    assert module["weight"] == 1


def test_edit_module_updates_all_values(admin_client):
    client, data = admin_client
    created = client.post("/api/academics/modules", json={
        "name": "Develop Website", "code": "SWDWD301", "hours": 100,
        "department_id": data["ict"].id, "trade_id": data["swd"].id, "level": "L3",
    }).get_json()["module"]
    response = client.put("/api/academics/modules/%d" % created["id"], json={
        "name": "Develop a dynamic Website", "code": "SWDWD302",
        "hours": 120, "periods": 180, "weight": 2.5, "category": "General",
    })
    assert response.status_code == 200, response.get_json()
    payload = response.get_json()["module"]
    assert payload["name"] == "Develop a dynamic Website"
    assert payload["code"] == "SWDWD302"
    assert payload["hours"] == 120
    assert payload["periods"] == 180
    assert payload["weight"] == 2.5
    assert payload["category"] == "General"
    stored = db.session.get(AcademicModule, created["id"])
    assert stored.name == "Develop a dynamic Website"
    assert stored.level == "L3"


def test_duplicate_module_name_at_same_level_is_rejected(admin_client):
    client, data = admin_client
    body = {"name": "Develop Website", "code": "SWDWD301", "hours": 50,
            "department_id": data["ict"].id, "trade_id": data["swd"].id, "level": "L3"}
    assert client.post("/api/academics/modules", json=body).status_code == 201
    duplicate = client.post("/api/academics/modules", json=body)
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.get_json()["message"]


def test_module_requires_a_level(admin_client):
    client, data = admin_client
    response = client.post("/api/academics/modules", json={
        "name": "Orphan", "department_id": data["ict"].id,
        "trade_id": data["swd"].id,
    })
    assert response.status_code == 400
    assert "level" in response.get_json()["message"].lower()


def test_trade_must_belong_to_the_selected_department(admin_client):
    client, data = admin_client
    other = Department.query.filter_by(name="Accounting").first()
    response = client.post("/api/academics/modules", json={
        "name": "Mismatch", "department_id": other.id,
        "trade_id": data["swd"].id, "level": "L3",
    })
    assert response.status_code == 400
    assert "department" in response.get_json()["message"].lower()


def test_delete_module_soft_removes_it_from_the_list(admin_client):
    client, data = admin_client
    module = client.post("/api/academics/modules", json={
        "name": "Remove Me", "department_id": data["ict"].id,
        "trade_id": data["swd"].id, "level": "L4",
    }).get_json()["module"]
    response = client.delete("/api/academics/modules/%d" % module["id"])
    assert response.status_code == 200
    listed = client.get("/api/academics/modules?level=L4&trade_id=%d" % data["swd"].id).get_json()
    assert listed == []
    # The row is kept (inactive) so historical references survive.
    assert db.session.get(AcademicModule, module["id"]).is_active is False


def test_students_cannot_change_modules(student_client):
    client, data = student_client
    response = client.post("/api/academics/modules", json={
        "name": "Not Allowed", "department_id": data["ict"].id,
        "trade_id": data["swd"].id, "level": "L3",
    })
    assert response.status_code == 403
    assert AcademicModule.query.count() == 0


def test_module_service_validates_unknown_scope(module_app):
    app, _ = module_app
    with app.app_context():
        with pytest.raises(AcademicValidationError):
            create_module(name="Ghost", department_id=999, level="L3")
        with pytest.raises(AcademicValidationError):
            update_module(999, name="Ghost")
        with pytest.raises(AcademicValidationError):
            delete_module(999)


def test_classes_modules_page_offers_relational_dropdowns(admin_client):
    client, data = admin_client
    create_module(name="Develop Website", code="SWDWD301", hours=110,
                  department_id=data["ict"].id, trade_id=data["swd"].id, level="L3")
    db.session.commit()
    html = client.get("/classes-modules").get_data(as_text=True)
    assert 'data-academic="department"' in html
    assert 'data-academic="trade"' in html
    assert 'data-academic="level"' in html
    assert 'data-academic="class"' in html
    assert "/static/js/academic-cascade.js" in html
    assert "const CAN_EDIT=true;" in html


def test_classes_modules_page_hides_actions_for_read_only_roles(student_client):
    client, _ = student_client
    html = client.get("/classes-modules").get_data(as_text=True)
    assert "const CAN_EDIT=false;" in html
