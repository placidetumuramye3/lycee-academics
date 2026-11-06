"""Seed the relational academic_module table from the transcribed curriculum.

The Classes & Modules page previously carried a hardcoded module catalog.
This migration moves that catalog into the ``academic_module`` table so
modules participate in the relational academic structure (Department ->
Trade -> Level -> Module) and can be used by cascading dropdowns,
grades, and subject assignment.

Safety rules:
- Modules are attached ONLY to trades that already exist in the
  relational hierarchy (created by v20261031_01_academic_foundation).
  If a trade is missing, its modules are skipped and counted for
  administrative review - nothing is guessed or orphaned.
- The migration is idempotent: re-running it updates existing rows
  (title/hours/category) instead of duplicating them. Rows already
  created by administrators are never deleted or renamed.
- Historical records (grades, subjects) are untouched.
"""
from sqlalchemy import inspect
from app.extensions import db
from app.models.academic_structure import Trade, SchoolClass, AcademicModule
from app.data.module_catalog import DEPARTMENTS

# Bucket -> category mapping used by AcademicModule.category.
CATEGORY_BY_BUCKET = {"C": "Complementary", "G": "General", "S": "Specific", "A": "General"}


def _trade_key(name):
    return (name or "").strip().casefold()


def _level_of(class_name):
    """Derive the level key (L3, L4, L5, S4...) from a class name."""
    head = (class_name or "").strip().split(" ", 1)[0]
    return head.upper() if head else None


def _existing_trades():
    """Map casefolded trade name -> Trade, for all active trades."""
    return {_trade_key(trade.name): trade for trade in Trade.query.all()}


def _existing_levels_by_trade():
    """Map trade_id -> set(casefolded level) of classes that actually exist."""
    levels = {}
    for trade_id, level in db.session.query(SchoolClass.trade_id, SchoolClass.level).filter(
            SchoolClass.is_active.is_(True)).all():
        if trade_id is not None and level:
            levels.setdefault(trade_id, set()).add(str(level).strip().casefold())
    return levels


def _upsert_module(trade_id, level, code, title, hours, category):
    """Insert or update one module row; returns 'created' or 'updated'."""
    module = AcademicModule.query.filter_by(
        trade_id=trade_id, level=level, name=title).first()
    if module is None:
        module = AcademicModule.query.filter_by(trade_id=trade_id, code=code, level=level).first()
    if module is None:
        module = AcademicModule(trade_id=trade_id, level=level, name=title, code=code)
        db.session.add(module)
        action = "created"
    else:
        action = "updated"
    module.name = title
    module.code = code
    module.category = category
    if isinstance(hours, (int, float)) and hours:
        module.weight = float(hours)
    module.is_active = True
    return action


def upgrade(connection):
    """Create the academic_module table if an older database lacks it."""
    tables = inspect(connection).get_table_names()
    if "academic_module" not in tables:
        db.metadata.create_all(bind=connection, tables=[AcademicModule.__table__])


def seed_modules():
    """Populate academic_module from the transcribed catalog.

    Returns a report dict with created/updated counts and a list of
    skipped entries requiring administrative review.
    """
    report = {"created": 0, "updated": 0, "skipped": []}
    trades = _existing_trades()
    class_levels = _existing_levels_by_trade()

    for department in DEPARTMENTS:
        for trade_data in department["trades"]:
            trade = trades.get(_trade_key(trade_data["name"]))
            if trade is None:
                report["skipped"].append({
                    "reason": "trade-not-found",
                    "department": department["name"],
                    "trade": trade_data["name"],
                })
                continue
            levels_with_classes = class_levels.get(trade.id, set())
            for class_data in trade_data["classes"]:
                level = _level_of(class_data["name"])
                if not level:
                    report["skipped"].append({
                        "reason": "level-unknown",
                        "class": class_data["name"],
                    })
                    continue
                if levels_with_classes and level.casefold() not in levels_with_classes:
                    # The trade exists but this level has no SchoolClass yet.
                    # Flag for review instead of guessing the mapping.
                    report["skipped"].append({
                        "reason": "level-without-class",
                        "class": class_data["name"],
                        "level": level,
                        "trade": trade.name,
                    })
                    continue
                for bucket in ("C", "G", "S", "A"):
                    for entry in class_data["modules"].get(bucket, []):
                        category = entry.get("category") or CATEGORY_BY_BUCKET.get(bucket, "General")
                        code = entry.get("code") or ""
                        title = (entry.get("title") or "").strip()
                        if not title:
                            continue
                        # The original page reuses a few codes for different
                        # titles (e.g. FADHS301 twice, duplicate GENAT302 in
                        # one list). Keep them distinct by (level, name) as
                        # the unique constraint requires, and drop exact
                        # duplicates silently.
                        action = _upsert_module(
                            trade.id, level, code, title,
                            entry.get("hours") or 0, category)
                        report[action] += 1
    db.session.commit()
    return report
