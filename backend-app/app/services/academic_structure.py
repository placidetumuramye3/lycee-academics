from app.extensions import db
from app.models import AcademicEnrollment, AcademicYear, Department, SchoolClass, Trade
from app.utils.constants import (
    CLASS_DEPARTMENT,
    CLASS_TRADE_LEVEL,
    LEGACY_CLASS_ALIASES,
)


_CANONICAL_CLASS_NAMES = {name.casefold(): name for name in CLASS_TRADE_LEVEL}
_LEGACY_CLASS_NAMES = {name.casefold(): canonical for name, canonical in LEGACY_CLASS_ALIASES.items()}


def canonical_class_name(value):
    normalized = (value or "").strip().casefold()
    return _CANONICAL_CLASS_NAMES.get(normalized) or _LEGACY_CLASS_NAMES.get(normalized)


def sync_student_enrollment(student):
    class_name = canonical_class_name(student.class_name)
    if not class_name:
        return None

    trade_name, _level = CLASS_TRADE_LEVEL[class_name]
    department_name = CLASS_DEPARTMENT[class_name]
    school_class = (
        SchoolClass.query.join(Trade).join(Department)
        .filter(
            db.func.lower(SchoolClass.name) == class_name.casefold(),
            db.func.lower(Trade.name) == trade_name.casefold(),
            db.func.lower(Department.name) == department_name.casefold(),
        )
        .first()
    )
    if not school_class:
        return None

    year_name = (student.academic_year or "").strip()
    academic_year = AcademicYear.query.filter_by(name=year_name).first() if year_name else None
    if academic_year is None and not year_name:
        academic_year = AcademicYear.query.filter_by(is_current=True).order_by(AcademicYear.name.desc()).first()
        if academic_year is None:
            academic_year = AcademicYear.query.order_by(AcademicYear.name.desc()).first()
    if academic_year is None and year_name:
        academic_year = AcademicYear(name=year_name, is_current=not AcademicYear.query.filter_by(is_current=True).first())
        db.session.add(academic_year)
        db.session.flush()
    if academic_year is None:
        return None

    enrollment = AcademicEnrollment.query.filter_by(
        student_id=student.id,
        academic_year_id=academic_year.id,
    ).first()
    if enrollment is None:
        enrollment = AcademicEnrollment(
            student_id=student.id,
            academic_year_id=academic_year.id,
        )
        db.session.add(enrollment)
    enrollment.department_id = school_class.trade.department_id
    enrollment.trade_id = school_class.trade_id
    enrollment.class_id = school_class.id
    enrollment.status = "active"
    return enrollment