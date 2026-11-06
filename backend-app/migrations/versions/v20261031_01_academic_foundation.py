"""Create the relational academic hierarchy and backfill current student placement."""
from sqlalchemy import inspect
from app.models.academic_structure import School, Department, Trade, SchoolClass, AcademicYear, AcademicTerm
from app.models.enrollment import AcademicEnrollment
from app.models.user import User
from app.extensions import db

SCHOOL_NAME = "Lycée de Muhura / Lycée Saint Alexandre Sauli"
STRUCTURE = {
    "ICT and Multimedia": {
        "Software Development": ["L3 SOFTWARE DEVELOPMENT", "L4 SOFTWARE DEVELOPMENT A", "L4 SOFTWARE DEVELOPMENT B", "L5 SOFTWARE DEVELOPMENT"],
        "Networking and Internet Technology": ["L3 NETWORKING AND INTERNET TECHNOLOGY", "L4 NETWORKING AND INTERNET TECHNOLOGY A", "L4 NETWORKING AND INTERNET TECHNOLOGY B", "L5 NETWORKING AND INTERNET TECHNOLOGY"],
        "Computer System and Architecture": ["L3 COMPUTER SYSTEM AND ARCHITECTURE", "L4 COMPUTER SYSTEM AND ARCHITECTURE", "L5 COMPUTER SYSTEM AND ARCHITECTURE"],
    },
    "Fashion and Design": {
        "Fashion and Design": ["L3 FASHION AND DESIGN", "L4 FASHION AND DESIGN", "L5 FASHION AND DESIGN"],
    },
    "Accounting": {
        "Accounting": ["S4 ACCOUNTANT A", "S4 ACCOUNTANT B", "S5 ACCOUNTANT", "S6 ACCOUNTANT"],
    },
}
# Earlier releases seeded these department/trade names in upper case (or as
# "Professional Accountant"). They are renamed - never duplicated - so existing
# classes, modules and enrollments keep their relationships intact.
LEGACY_NAMES = {
    "department": {"ICT AND MULTIMEDIA": "ICT and Multimedia",
                   "FASHION AND DESIGN": "Fashion and Design",
                   "PROFESSIONAL ACCOUNTANT": "Accounting"},
    "trade": {"SOFTWARE DEVELOPMENT": "Software Development",
              "NETWORKING AND INTERNET TECHNOLOGY": "Networking and Internet Technology",
              "COMPUTER SYSTEM AND ARCHITECTURE": "Computer System and Architecture",
              "FASHION AND DESIGN": "Fashion and Design",
              "PROFESSIONAL ACCOUNTANT": "Accounting"},
}


def upgrade(connection):
    # The app's db metadata is authoritative for these new tables.
    db.metadata.create_all(bind=connection, tables=[
        School.__table__, Department.__table__, Trade.__table__, SchoolClass.__table__,
        AcademicYear.__table__, AcademicTerm.__table__, AcademicEnrollment.__table__,
    ])


def normalize_department_trade_names():
    """Rename legacy department/trade rows to the canonical names."""
    for model, names in ((Department, LEGACY_NAMES["department"]),
                         (Trade, LEGACY_NAMES["trade"])):
        for old_name, new_name in names.items():
            for row in model.query.filter_by(name=old_name).all():
                scope = {"school_id": row.school_id} if model is Department \
                    else {"department_id": row.department_id}
                if model.query.filter_by(name=new_name, **scope).first() is None:
                    row.name = new_name
    db.session.flush()


def seed_and_backfill():
    normalize_department_trade_names()
    school = School.query.filter_by(name=SCHOOL_NAME).first()
    if not school:
        school = School(name=SCHOOL_NAME, code="LYCEE-MUHURA")
        db.session.add(school)
        db.session.flush()
    departments = {}
    trades = {}
    classes = {}
    for dept_name, trade_map in STRUCTURE.items():
        dept = Department.query.filter_by(school_id=school.id, name=dept_name).first()
        if not dept:
            dept = Department(school_id=school.id, name=dept_name)
            db.session.add(dept); db.session.flush()
        departments[dept_name] = dept
        for trade_name, class_names in trade_map.items():
            trade = Trade.query.filter_by(department_id=dept.id, name=trade_name).first()
            if not trade:
                trade = Trade(department_id=dept.id, name=trade_name)
                db.session.add(trade); db.session.flush()
            trades[trade_name] = trade
            for class_name in class_names:
                level = class_name.split(" ", 1)[0]
                cls = SchoolClass.query.filter_by(trade_id=trade.id, name=class_name).first()
                if not cls:
                    cls = SchoolClass(trade_id=trade.id, name=class_name, level=level,
                                      code=f"{dept.id}-{trade.id}-{class_name}")
                    db.session.add(cls); db.session.flush()
                classes[class_name.strip().upper()] = (dept, trade, cls)

    current_year_name = None
    rows = User.query.filter_by(role="student").all()
    for student in rows:
        year_name = (student.academic_year or "").strip()
        if year_name and not current_year_name:
            current_year_name = year_name
        class_candidates = [student.class_name, student.level]
        label = next((x.strip().upper() for x in class_candidates if x and x.strip()), None)
        if not label or label not in classes:
            continue
        if not year_name:
            year_name = current_year_name or "UNSPECIFIED"
        year = AcademicYear.query.filter_by(name=year_name).first()
        if not year:
            year = AcademicYear(name=year_name, is_current=(year_name == current_year_name))
            db.session.add(year); db.session.flush()
        dept, trade, cls = classes[label]
        existing = AcademicEnrollment.query.filter_by(student_id=student.id, academic_year_id=year.id).first()
        if not existing:
            db.session.add(AcademicEnrollment(student_id=student.id, academic_year_id=year.id,
                                               department_id=dept.id, trade_id=trade.id, class_id=cls.id,
                                               status="active"))
    db.session.commit()
