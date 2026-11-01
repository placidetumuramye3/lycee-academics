from app.extensions import db
from app.models import AcademicEnrollment, AcademicYear, SchoolClass, User
from app.utils.constants import CLASS_NAMES


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _user(username, role, class_name=None):
    return User(
        username=username,
        full_name=username.replace("_", " ").title(),
        password_hash="test-hash",
        role=role,
        class_name=class_name,
        is_active_account=True,
    )


def test_school_structure_shows_exact_canonical_class_list(app):
    with app.app_context():
        admin = _user("structure_admin", "master_admin")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    _login(client, admin_id)
    response = client.get("/school-structure")

    assert response.status_code == 200
    assert b"3 departments" in response.data
    assert b"5 trades" in response.data
    assert b"18 visible classes" in response.data
    for class_name in CLASS_NAMES:
        assert class_name.encode() in response.data
    assert b"S5 Professional Accountant A" not in response.data
    assert b"S5 Professional Accountant B" not in response.data


def test_teacher_structure_and_roster_are_limited_to_assigned_class(app):
    with app.app_context():
        assigned_name = "L3 SOFTWARE DEVELOPMENT"
        private_name = "L3 NETWORKING AND INTERNET TECHNOLOGY"
        assigned_class = SchoolClass.query.filter_by(name=assigned_name).one()
        private_class = SchoolClass.query.filter_by(name=private_name).one()
        year = AcademicYear(name="2026-2027", is_current=True)
        teacher = _user("structure_teacher", "teacher", "L3 Software Development")
        assigned_student = _user("assigned_student", "student", "L3 Software Development")
        private_student = _user("private_student", "student", "L3 Networking and Internet Technology")
        assigned_student.academic_year = year.name
        private_student.academic_year = year.name
        assigned_student.trade = "Software Development"
        private_student.trade = "Networking and Internet Technology"
        assigned_student.level = private_student.level = "L3"
        db.session.add_all([year, teacher, assigned_student, private_student])
        db.session.flush()
        db.session.add_all([
            AcademicEnrollment(
                student_id=assigned_student.id,
                academic_year_id=year.id,
                department_id=assigned_class.trade.department_id,
                trade_id=assigned_class.trade_id,
                class_id=assigned_class.id,
            ),
            AcademicEnrollment(
                student_id=private_student.id,
                academic_year_id=year.id,
                department_id=private_class.trade.department_id,
                trade_id=private_class.trade_id,
                class_id=private_class.id,
            ),
        ])
        db.session.commit()
        teacher_id = teacher.id
        year_id = year.id
        class_id = assigned_class.id

    client = app.test_client()
    _login(client, teacher_id)
    response = client.get(f"/school-structure?year_id={year_id}&class_id={class_id}")

    assert response.status_code == 200
    assert b"Assigned Student" in response.data
    assert b"Private Student" not in response.data
    assert b"Networking and Internet Technology" not in response.data


def test_student_cannot_open_school_structure(app):
    with app.app_context():
        student = _user("structure_student", "student")
        db.session.add(student)
        db.session.commit()
        student_id = student.id

    client = app.test_client()
    _login(client, student_id)

    assert client.get("/school-structure").status_code == 403


def test_legacy_fashion_class_backfills_to_canonical_class(app):
    with app.app_context():
        student = _user("legacy_fashion_student", "student", "L4 Fashion Design")
        student.academic_year = "2026-2027"
        student.department = "Creative Arts"
        student.trade = "Fashion Design"
        student.level = "L4"
        db.session.add(student)
        db.session.commit()
        student_id = student.id

        from migrations.versions.v20261031_01_academic_foundation import seed_and_backfill

        seed_and_backfill()
        enrollment = AcademicEnrollment.query.filter_by(student_id=student_id).one()
        school_class = db.session.get(SchoolClass, enrollment.class_id)

        assert school_class.name == "L4 FASHION AND DESIGN"