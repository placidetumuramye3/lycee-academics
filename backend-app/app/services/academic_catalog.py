"""Centralized, database-driven academic relationship management.

All forms and APIs must use these helpers instead of hand-built option
lists so that departments, trades, levels, classes, and modules stay
relationally consistent across the whole application.

The relational hierarchy (School -> Department -> Trade -> SchoolClass,
with AcademicModule attached to a trade + level) is authoritative. The
static SCHOOL_STRUCTURE constants are used only as a bootstrap seed and
as a read-only fallback when the database has not been seeded yet.
"""
from app.extensions import db
from app.models.academic_structure import (
    Department, Trade, SchoolClass, AcademicModule,
)


def _active(query):
    return query.filter_by(is_active=True)


def get_departments():
    """All active departments, alphabetically."""
    return _active(Department.query).order_by(Department.name).all()


def get_department(department_id):
    return _active(Department.query).filter_by(id=department_id).first()


def get_trades_by_department(department_id):
    """Active trades belonging to one department only."""
    return (
        _active(Trade.query)
        .filter(Trade.department_id == department_id)
        .order_by(Trade.name)
        .all()
    )


def get_trade(trade_id):
    return _active(Trade.query).filter_by(id=trade_id).first()


def get_levels_by_department(department_id):
    """Distinct levels offered across a department's trades."""
    rows = (
        db.session.query(SchoolClass.level)
        .join(Trade, SchoolClass.trade_id == Trade.id)
        .filter(Trade.department_id == department_id, Trade.is_active.is_(True),
                SchoolClass.is_active.is_(True))
        .distinct()
        .order_by(SchoolClass.level)
        .all()
    )
    return [row[0] for row in rows]


def get_levels_by_trade(trade_id):
    """Distinct levels that a trade offers (via its classes and modules)."""
    class_levels = {
        row[0]
        for row in db.session.query(SchoolClass.level)
        .filter(SchoolClass.trade_id == trade_id, SchoolClass.is_active.is_(True))
        .distinct()
    }
    module_levels = {
        row[0]
        for row in db.session.query(AcademicModule.level)
        .filter(AcademicModule.trade_id == trade_id, AcademicModule.is_active.is_(True))
        .distinct()
    }
    return sorted(class_levels | module_levels)


def get_classes_by_trade(trade_id, level=None):
    """Active classes of a trade, optionally narrowed to one level."""
    query = _active(SchoolClass.query).filter(SchoolClass.trade_id == trade_id)
    if level:
        query = query.filter(SchoolClass.level == level)
    return query.order_by(SchoolClass.level, SchoolClass.name).all()


def get_classes_by_level(department_id=None, trade_id=None, level=None):
    """Classes matching an academic combination. All filters are ANDed."""
    query = _active(SchoolClass.query).join(Trade, SchoolClass.trade_id == Trade.id)
    if department_id:
        query = query.filter(Trade.department_id == department_id)
    if trade_id:
        query = query.filter(SchoolClass.trade_id == trade_id)
    if level:
        query = query.filter(SchoolClass.level == level)
    return query.order_by(SchoolClass.name).all()


def get_class(class_id):
    return _active(SchoolClass.query).filter_by(id=class_id).first()


def get_modules_by_trade(trade_id, level=None):
    """Modules assigned to a trade, optionally narrowed to one level."""
    query = _active(AcademicModule.query).filter(AcademicModule.trade_id == trade_id)
    if level:
        query = query.filter(AcademicModule.level == level)
    return query.order_by(AcademicModule.level, AcademicModule.name).all()


def get_modules_by_department(department_id, level=None):
    """Modules across all trades of a department, optionally per level."""
    query = _active(AcademicModule.query).join(Trade, AcademicModule.trade_id == Trade.id)
    query = query.filter(Trade.department_id == department_id, Trade.is_active.is_(True))
    if level:
        query = query.filter(AcademicModule.level == level)
    return query.order_by(AcademicModule.level, AcademicModule.name).all()


def get_modules_by_class(class_id):
    """Modules that apply to a class: its trade's modules for that class level."""
    klass = get_class(class_id)
    if not klass:
        return []
    return get_modules_by_trade(klass.trade_id, klass.level)


def get_class_context(class_id):
    """Return (department, trade, class) for a class id, or (None, None, None)."""
    klass = get_class(class_id)
    if not klass:
        return None, None, None
    trade = get_trade(klass.trade_id)
    department = trade and get_department(trade.department_id)
    return department, trade, klass


def full_structure():
    """Nested structure for cascading dropdowns, in one round trip.

    Returns a list of departments, each with trades, levels, classes and
    modules pre-nested so the frontend needs a single request.
    """
    data = []
    for department in get_departments():
        dept_data = {
            "id": department.id, "name": department.name, "code": department.code,
            "trades": [],
        }
        for trade in get_trades_by_department(department.id):
            trade_data = {"id": trade.id, "name": trade.name, "code": trade.code, "levels": {}}
            for klass in get_classes_by_trade(trade.id):
                level = trade_data["levels"].setdefault(
                    klass.level, {"classes": [], "modules": []})
                level["classes"].append({"id": klass.id, "name": klass.name,
                                         "section": klass.section})
            for module in get_modules_by_trade(trade.id):
                level = trade_data["levels"].setdefault(
                    module.level, {"classes": [], "modules": []})
                level["modules"].append({"id": module.id, "name": module.name,
                                         "code": module.code, "category": module.category})
            dept_data["trades"].append(trade_data)
        data.append(dept_data)
    return data


class AcademicValidationError(ValueError):
    """Raised when a submitted academic combination is invalid."""


def validate_placement(trade_name, level, class_name):
    """Validate a name-based placement (student records keep names).

    Returns the canonical (department, trade, level, class_name) tuple.
    Raises AcademicValidationError with a user-friendly message when the
    combination is not part of the relational academic structure.
    """
    from app.utils.constants import CLASS_TRADE_LEVEL, TRADE_DEPARTMENT

    trade_name = (trade_name or "").strip()
    level = (level or "").strip()
    class_name = (class_name or "").strip()

    klass = _active(SchoolClass.query).filter(
        db.func.lower(SchoolClass.name) == class_name.casefold()
    ).first() if class_name else None

    if klass:
        trade = get_trade(klass.trade_id)
        department = trade and get_department(trade.department_id)
        if not trade or not department:
            raise AcademicValidationError(
                "The selected class is not linked to an active trade and department.")
        if trade_name and trade_name.casefold() != trade.name.casefold():
            raise AcademicValidationError(
                "The selected class does not belong to the selected trade.")
        if level and level.casefold() != (klass.level or "").casefold():
            raise AcademicValidationError(
                "The selected class does not belong to the selected level.")
        return department.name, trade.name, klass.level, klass.name

    # Class not in the relational database: fall back to the seeded
    # structure so legacy records keep working, but never guess.
    expected = CLASS_TRADE_LEVEL.get(class_name) if class_name else None
    if class_name and not expected:
        raise AcademicValidationError(
            "The selected class is not part of the school academic structure.")
    if expected:
        trade_name = trade_name or expected[0]
        level = level or expected[1]
    if expected and ((trade_name.casefold(), level.casefold()) !=
                     (expected[0].casefold(), expected[1].casefold())):
        raise AcademicValidationError(
            "Choose a class that belongs to the selected trade and level.")
    department_name = next(
        (name for name in TRADE_DEPARTMENT
         if name.casefold() == (trade_name or "").casefold()),
        None,
    )
    if not department_name:
        raise AcademicValidationError("Choose a valid trade.")
    return department_name, TRADE_DEPARTMENT[department_name], level, class_name


def validate_module_assignment(trade_id, level, module_id=None):
    """Ensure a module belongs to the given trade and level."""
    query = _active(AcademicModule.query).filter(AcademicModule.trade_id == trade_id)
    if module_id:
        module = query.filter(AcademicModule.id == module_id).first()
        if not module:
            raise AcademicValidationError(
                "The selected module is not assigned to this trade.")
        if level and module.level.casefold() != level.casefold():
            raise AcademicValidationError(
                "The selected module does not belong to the selected level.")
        return module
    return None


def validate_teacher_assignment(trade_name, level, class_name, subject):
    # Resolve a staff lesson against the active relational module catalogue.
    klass = (
        SchoolClass.query.join(Trade).join(Department).join(Department.school)
        .filter(
            db.func.lower(SchoolClass.name) == class_name.lower(),
            db.func.lower(SchoolClass.level) == level.lower(),
            db.func.lower(Trade.name) == trade_name.lower(), SchoolClass.is_active.is_(True),
            Trade.is_active.is_(True), Department.is_active.is_(True),
            Department.school.has(is_active=True),
        ).first()
    )
    if not klass:
        raise AcademicValidationError("Choose an active class in the selected trade and level.")
    module = AcademicModule.query.filter(
        AcademicModule.trade_id == klass.trade_id,
        db.func.lower(AcademicModule.level) == klass.level.casefold(),
        db.func.lower(AcademicModule.name) == subject.lower(),
        AcademicModule.is_active.is_(True),
    ).first()
    if not module:
        raise AcademicValidationError("Choose a module offered for the selected class, trade, and level.")
    return klass.trade.name, klass.level, klass.name, module.name


# ---------------------------------------------------------------------------
# Module maintenance
#
# Modules are always reached through their relational anchors
# (department -> trade -> level -> class). A module is stored on
# (trade, level); classes inherit every module of their own level, so an
# edit made from any class page immediately applies to the whole level.
# ---------------------------------------------------------------------------

MODULE_CATEGORIES = ("Complementary", "General", "Specific")


def normalize_category(value):
    """Map free-text category labels onto the stored canonical values."""
    text = (value or "").strip().casefold()
    if not text:
        return "Specific"  # the default bucket for new modules
    if text in ("c", "complementary", "complementary module", "complementary modules"):
        return "Complementary"
    if text in ("g", "general", "general module", "general modules", "all", "a", "all subjects"):
        return "General"
    if text in ("s", "specific", "specific (core)", "core", "specific module",
                "specific modules", "specific (core) modules"):
        return "Specific"
    raise AcademicValidationError("Choose a valid module category.")


def _positive_number(value, label):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise AcademicValidationError("%s must be a number." % label)
    if number < 0:
        raise AcademicValidationError("%s cannot be negative." % label)
    return number


def resolve_module_scope(department_id=None, trade_id=None, level=None, class_id=None):
    """Return (department, trade, level) for the submitted selection.

    The anchors are ANDed: a trade must belong to the chosen department and a
    class must belong to the chosen trade/level. Nothing is guessed.
    """
    department = trade = None
    if class_id:
        department, trade, klass = get_class_context(class_id)
        if not klass:
            raise AcademicValidationError("The selected class no longer exists.")
        if trade_id and trade.id != int(trade_id):
            raise AcademicValidationError(
                "The selected class does not belong to the selected trade.")
        if level and klass.level.casefold() != str(level).strip().casefold():
            raise AcademicValidationError(
                "The selected class does not belong to the selected level.")
        return department, trade, klass.level
    if trade_id:
        trade = get_trade(trade_id)
        if not trade:
            raise AcademicValidationError("The selected trade no longer exists.")
        department = get_department(trade.department_id)
        if not department:
            raise AcademicValidationError(
                "The selected trade is not linked to an active department.")
        if department_id and department.id != int(department_id):
            raise AcademicValidationError(
                "The selected trade does not belong to the selected department.")
    elif department_id:
        department = get_department(department_id)
        if not department:
            raise AcademicValidationError("The selected department no longer exists.")
    else:
        raise AcademicValidationError(
            "Choose a department, or a trade/class, before saving a module.")
    level = (str(level).strip() if level else "")
    if not level:
        raise AcademicValidationError("Choose the level this module is taught at.")
    return department, trade, level


def _check_unique(trade_id, level, name, code, exclude_id=None):
    query = AcademicModule.query.filter(
        AcademicModule.trade_id == trade_id,
        db.func.lower(AcademicModule.level) == level.casefold(),
        db.func.lower(AcademicModule.name) == name.casefold(),
        AcademicModule.is_active.is_(True),
    )
    if exclude_id:
        query = query.filter(AcademicModule.id != exclude_id)
    if query.first():
        raise AcademicValidationError(
            "A module named \"%s\" already exists for this trade and level." % name)
    if code:
        code_query = _active(AcademicModule.query).filter(
            AcademicModule.trade_id == trade_id,
            db.func.lower(AcademicModule.level) == level.casefold(),
            db.func.lower(AcademicModule.code) == code.casefold(),
        )
        if exclude_id:
            code_query = code_query.filter(AcademicModule.id != exclude_id)
        if code_query.first():
            raise AcademicValidationError(
                "The module code \"%s\" is already used at this level." % code)


def create_module(name, code=None, hours=None, periods=None, weight=None,
                  category="Specific", department_id=None, trade_id=None,
                  level=None, class_id=None):
    department, trade, level = resolve_module_scope(
        department_id, trade_id, level, class_id)
    name = (name or "").strip()
    if not name:
        raise AcademicValidationError("Module name is required.")
    code = (code or "").strip().upper() or None
    category = normalize_category(category)
    hours = _positive_number(hours, "Hours")
    periods = _positive_number(periods, "Periods")
    weight = _positive_number(weight, "Weight")
    _check_unique(trade.id, level, name, code)
    module = AcademicModule(
        trade_id=trade.id,
        level=level,
        name=name,
        code=code,
        category=category,
    )
    apply_module_numbers(module, hours=hours, periods=periods, weight=weight)
    db.session.add(module)
    return module


def apply_module_numbers(module, hours, periods, weight):
    """Store hours/periods/weight consistently.

    ``AcademicModule.weight`` holds the teaching hours (the legacy column the
    Classes & Modules page displays as "Hours"). Periods (hours * 1.5) and the
    assessment weight are persisted on the module so every page reads the same
    values. Assessment weight defaults to 1 (as in the UI) when it is cleared.
    """
    if hours is None and periods is not None:
        hours = float(periods) / 1.5
    if hours is not None:
        module.weight = float(hours)
    if periods is not None:
        module.periods = float(periods)
    elif hours is not None:
        module.periods = float(hours) * 1.5
    if weight is not None:
        module.assessment_weight = float(weight)
    if module.assessment_weight is None:
        module.assessment_weight = 1.0


def update_module(module_id, **fields):
    module = _active(AcademicModule.query).filter_by(id=module_id).first()
    if not module:
        raise AcademicValidationError("The selected module no longer exists.")
    department = trade = level = None
    if any(fields.get(key) for key in ("department_id", "trade_id", "class_id")):
        department, trade, level = resolve_module_scope(
            fields.get("department_id"), fields.get("trade_id"),
            fields.get("level"), fields.get("class_id"))
    if level is None:
        trade = get_trade(module.trade_id)
        department = trade and get_department(trade.department_id)
        level = module.level
    if not trade:
        raise AcademicValidationError(
            "The module's trade no longer exists; choose a department and level.")
    name = (fields.get("name") or "").strip()
    if not name:
        raise AcademicValidationError("Module name is required.")
    code = (fields.get("code") or "").strip().upper() or None
    category = normalize_category(fields.get("category") or module.category)
    hours = _positive_number(fields.get("hours"), "Hours")
    periods = _positive_number(fields.get("periods"), "Periods")
    weight = _positive_number(fields.get("weight"), "Weight")
    _check_unique(trade.id, level, name, code, exclude_id=module.id)
    module.trade_id = trade.id
    module.level = level
    module.name = name
    module.code = code
    module.category = category
    apply_module_numbers(module, hours=hours, periods=periods, weight=weight)
    return module


def delete_module(module_id):
    """Soft-delete a module: historical grades keep their module reference."""
    module = _active(AcademicModule.query).filter_by(id=module_id).first()
    if not module:
        raise AcademicValidationError("The selected module no longer exists.")
    module.is_active = False
    return module


def serialize_module(module):
    trade = get_trade(module.trade_id)
    department = trade and get_department(trade.department_id)
    return {
        "id": module.id,
        "name": module.name,
        "code": module.code or "",
        "level": module.level,
        "category": module.category or "Specific",
        "hours": module.weight,
        "periods": module.periods if module.periods is not None
        else (float(module.weight) * 1.5 if module.weight else None),
        "weight": module.assessment_weight if module.assessment_weight is not None else 1.0,
        "department_id": department.id if department else None,
        "department": department.name if department else "",
        "trade_id": trade.id if trade else None,
        "trade": trade.name if trade else "",
        "class_ids": [klass.id for klass in get_classes_by_trade(module.trade_id, module.level)],
    }
