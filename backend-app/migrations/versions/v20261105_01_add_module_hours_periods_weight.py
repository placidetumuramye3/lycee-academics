"""Add explicit periods / assessment weight columns to academic_module.

``academic_module.weight`` historically stored the teaching hours. The
Classes & Modules page now lets administrators maintain hours, periods and
the assessment weight, so the extra values need their own columns.

Safety rules:
- Columns are only added when missing (idempotent, safe on Postgres/SQLite).
- Existing hours are kept untouched; periods are backfilled as hours * 1.5
  (the period length used across the school) and the assessment weight
  defaults to 1.0.
"""
from sqlalchemy import inspect, text
from app.extensions import db
from app.models.academic_structure import AcademicModule


def _add_column(connection, name, ddl):
    columns = {column["name"] for column in inspect(connection).get_columns("academic_module")}
    if name not in columns:
        connection.execute(text("ALTER TABLE academic_module ADD COLUMN %s %s" % (name, ddl)))
        return True
    return False


def upgrade(connection):
    tables = inspect(connection).get_table_names()
    if "academic_module" not in tables:
        db.metadata.create_all(bind=connection, tables=[AcademicModule.__table__])
        return
    added_periods = _add_column(connection, "periods", "FLOAT")
    added_weight = _add_column(connection, "assessment_weight", "FLOAT")
    _add_column(connection, "updated_at", "TIMESTAMP")
    if added_weight:
        connection.execute(text(
            "UPDATE academic_module SET assessment_weight = 1.0 WHERE assessment_weight IS NULL"))
    if added_periods:
        connection.execute(text(
            "UPDATE academic_module SET periods = weight * 1.5 "
            "WHERE periods IS NULL AND weight IS NOT NULL"))
