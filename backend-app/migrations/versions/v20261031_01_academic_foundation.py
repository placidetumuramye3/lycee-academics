"""Create the relational academic hierarchy and backfill current student placement."""
from sqlalchemy import inspect
from app.models.academic_structure import School, Department, Trade, SchoolClass, AcademicYear, AcademicTerm
from app.models.enrollment import AcademicEnrollment
from app.models.user import User
from app.extensions import db
from app.utils.constants import (
    CLASS_DEPARTMENT,
    CLASS_TRADE_LEVEL,
    LEGACY_CLASS_ALIASES,
    SCHOOL_STRUCTURE,
)

SCHOOL_NAME = "Lycée de Muhura / Lycée Saint Alexandre Sauli"
STRUCTURE = {
    department.upper(): {
        trade.upper(): [class_name.upper() for levels in level_map.values() for class_name in levels]
        for trade, level_map in trade_map.items()
    }
    for department, trade_map in SCHOOL_STRUCTURE.items()
}
LEGACY_CLASS_ALIASES_UPPER = {
    legacy.upper(): canonical.upper()
    for legacy, canonical in LEGACY_CLASS_ALIASES.items()
}
CANONICAL_CLASS_NAMES_UPPER = {name.upper(): name for name in CLASS_TRADE_LEVEL}


def upgrade(connection):
    # The app's db metadata is authoritative for these new tables.
    db.metadata.create_all(bind=connection, tables=[
        School.__table__, Department.__table__, Trade.__table__, SchoolClass.__table__,
        AcademicYear.__table__, AcademicTerm.__table__, AcademicEnrollment.__table__,
    ])


def seed_and_backfill():
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
                section = None
                if class_name.endswith(" A"):
                    section = "A"
                elif class_name.endswith(" B"):
                    section = "B"
                cls = SchoolClass.query.filter_by(trade_id=trade.id, name=class_name).first()
                if not cls:
                    cls = SchoolClass(trade_id=trade.id, name=class_name, level=level, section=section,
                                      code=f"{dept.id}-{trade.id}-{class_name}")
                    db.session.add(cls); db.session.flush()
                classes[class_name.strip().upper()] = (dept, trade, cls)

    for legacy_name, canonical_upper in LEGACY_CLASS_ALIASES_UPPER.items():
        canonical_name = CANONICAL_CLASS_NAMES_UPPER[canonical_upper]
        trade_name, level = CLASS_TRADE_LEVEL[canonical_name]
        department_name = CLASS_DEPARTMENT[canonical_name]
        values = {"class_name": canonical_name}
        for column_name, value in (
            ("department", department_name),
            ("trade", trade_name),
            ("level", level),
        ):
            if column_name in User.__table__.c:
                values[column_name] = value
        if legacy_name.endswith((" A", " B")) and "class_section" in User.__table__.c:
            section = legacy_name[-1]
            db.session.execute(
                User.__table__.update()
                .where(
                    db.func.lower(User.__table__.c.class_name) == legacy_name.casefold(),
                    User.__table__.c.class_section.is_(None),
                )
                .values(class_section=section)
            )
        for table in db.metadata.tables.values():
            class_column = table.c.get("class_name")
            if class_column is None:
                continue
            update_values = {"class_name": canonical_name}
            update_values.update({name: value for name, value in values.items() if name in table.c})
            db.session.execute(
                table.update()
                .where(db.func.lower(class_column) == legacy_name.casefold())
                .values(**update_values)
            )

    current_year_name = None
    rows = User.query.filter_by(role="student").all()
    for student in rows:
        year_name = (student.academic_year or "").strip()
        if year_name and not current_year_name:
            current_year_name = year_name
        class_candidates = [student.class_name, student.class_section]
        label = next((x.strip().upper() for x in class_candidates if x and x.strip()), None)
        label = LEGACY_CLASS_ALIASES_UPPER.get(label, label)
        if label not in classes:
            # Some legacy records store only level + class section.
            legacy = " ".join(x for x in [student.level, student.class_section] if x).strip().upper()
            label = legacy if legacy in classes else label
        if not label or label not in classes:
            continue
        canonical_name = CANONICAL_CLASS_NAMES_UPPER.get(label)
        if canonical_name:
            dept, trade, cls = classes[label]
            student.class_name = canonical_name
            student.department = CLASS_DEPARTMENT[canonical_name]
            student.trade = CLASS_TRADE_LEVEL[canonical_name][0]
            student.level = CLASS_TRADE_LEVEL[canonical_name][1]
            if not student.class_section and class_candidates[0]:
                legacy_name = class_candidates[0].strip().upper()
                if legacy_name.endswith((" A", " B")):
                    student.class_section = legacy_name[-1]
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
