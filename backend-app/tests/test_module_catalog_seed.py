"""Tests for the module catalog migration and the Classes & Modules page."""
import pytest
from app.extensions import db
from app.models.academic_structure import (
    School, Department, Trade, SchoolClass, AcademicModule,
)
from migrations.versions.v20261103_01_seed_academic_modules import (
    seed_modules, _level_of,
)
from app.data.module_catalog import DEPARTMENTS


@pytest.fixture
def hierarchy_app():
    from app import create_app
    from tests.conftest import TestConfig

    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_hierarchy():
    """Create the relational hierarchy matching the catalog (title case)."""
    school = School(name="Seed School", code="SS")
    db.session.add(school)
    db.session.flush()
    made = {}
    for department in DEPARTMENTS:
        dept = Department(school_id=school.id, name=department["name"])
        db.session.add(dept)
        db.session.flush()
        for trade in department["trades"]:
            trade_row = Trade(department_id=dept.id, name=trade["name"])
            db.session.add(trade_row)
            db.session.flush()
            for class_data in trade["classes"]:
                db.session.add(SchoolClass(
                    trade_id=trade_row.id,
                    name=class_data["name"].upper(),
                    level=_level_of(class_data["name"])))
            made[trade["name"]] = trade_row
    db.session.commit()
    return made


def test_level_of_extracts_level_key():
    assert _level_of("L3 Software Development") == "L3"
    assert _level_of("S4 Accountant A") == "S4"
    assert _level_of("") is None


def test_seed_creates_modules_linked_to_trades(hierarchy_app):
    with hierarchy_app.app_context():
        _make_hierarchy()
        report = seed_modules()
        assert report["created"] > 0
        assert not report["skipped"], report["skipped"]
        swd = Trade.query.filter_by(name="Software Development").first()
        modules = AcademicModule.query.filter_by(trade_id=swd.id, level="L3").all()
        titles = {m.name for m in modules}
        assert "Develop Website" in titles
        # Complementary modules assigned to the L3 level.
        assert "Use Pre-intermediate English at the Workplace" in titles


def test_seed_is_idempotent(hierarchy_app):
    with hierarchy_app.app_context():
        _make_hierarchy()
        first = seed_modules()
        total_after_first = AcademicModule.query.count()
        assert first["created"] > 0
        second = seed_modules()
        # Re-running must not create or delete anything - only update.
        assert second["created"] == 0
        assert second["updated"] >= 0
        assert AcademicModule.query.count() == total_after_first


def test_seed_skips_missing_trades(hierarchy_app):
    with hierarchy_app.app_context():
        # No hierarchy created at all: everything is flagged for review.
        report = seed_modules()
        assert report["created"] == 0
        skipped_trades = [s for s in report["skipped"] if s["reason"] == "trade-not-found"]
        assert skipped_trades, "missing trades must be flagged, not guessed"


def test_seed_does_not_create_orphan_modules(hierarchy_app):
    with hierarchy_app.app_context():
        _make_hierarchy()
        # Delete one level of classes to simulate incomplete configuration.
        SchoolClass.query.filter_by(level="L5").delete()
        db.session.commit()
        report = seed_modules()
        flagged = [s for s in report["skipped"] if s["reason"] == "level-without-class"]
        assert flagged
        l5_levels = AcademicModule.query.filter_by(level="L5").count()
        assert l5_levels == 0


def test_classes_modules_page_renders_from_db(hierarchy_app):
    with hierarchy_app.app_context():
        _make_hierarchy()
        seed_modules()
        from app.routes.classes_modules import _catalog_from_database
        catalog, db_backed = _catalog_from_database()
        assert db_backed
        ict = next(d for d in catalog if d["n"] == "ICT and Multimedia")
        assert ict["t"], "ICT trades must be present"
        class_names = [c[0] for t in ict["t"] for c in t["c"]]
        assert "L3 SOFTWARE DEVELOPMENT" in class_names
        swd3 = next(c for t in ict["t"] if t["n"] == "Software Development"
                    for c in t["c"] if "L3" in c[0])
        titles = [m["title"] for m in swd3[1]["S"]]
        assert "Develop Website" in titles


def test_classes_modules_page_falls_back_when_db_empty(hierarchy_app):
    with hierarchy_app.app_context():
        from app.routes.classes_modules import _catalog_from_database, _catalog_from_fallback
        catalog, db_backed = _catalog_from_database()
        assert not db_backed
        fallback = _catalog_from_fallback()
        assert fallback, "fallback catalog must always be available"
