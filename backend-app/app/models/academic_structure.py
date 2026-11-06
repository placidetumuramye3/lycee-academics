"""Relational academic hierarchy for the Smart School target architecture."""
from app.extensions import db
from datetime import datetime


class School(db.Model):
    __tablename__ = "school"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    code = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    departments = db.relationship("Department", backref="school", cascade="all, delete-orphan")


class Department(db.Model):
    __tablename__ = "department"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("school.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    code = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint("school_id", "name", name="uq_department_school_name"),)
    trades = db.relationship("Trade", backref="department", cascade="all, delete-orphan")


class Trade(db.Model):
    __tablename__ = "trade"
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    code = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint("department_id", "name", name="uq_trade_department_name"),)
    classes = db.relationship("SchoolClass", backref="trade", cascade="all, delete-orphan")


class SchoolClass(db.Model):
    __tablename__ = "school_class"
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer, db.ForeignKey("trade.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    level = db.Column(db.String(30), nullable=False)
    code = db.Column(db.String(80), unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint("trade_id", "name", name="uq_class_trade_name"),)


class AcademicModule(db.Model):
    __tablename__ = "academic_module"
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer, db.ForeignKey("trade.id"), nullable=False, index=True)
    level = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    code = db.Column(db.String(50))
    category = db.Column(db.String(32), default="Specific")
    # ``weight`` holds the teaching hours (legacy column name). Periods and the
    # assessment weight are stored explicitly so every page agrees.
    weight = db.Column(db.Float, default=1.0)
    periods = db.Column(db.Float)
    assessment_weight = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trade = db.relationship("Trade", backref=db.backref("modules", cascade="all, delete-orphan"))
    __table_args__ = (db.UniqueConstraint("trade_id", "level", "name", name="uq_module_trade_level_name"),)


class AcademicYear(db.Model):
    __tablename__ = "academic_year"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, nullable=False, default=False)


class AcademicTerm(db.Model):
    __tablename__ = "academic_term"
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_year.id"), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, nullable=False, default=False)
    academic_year = db.relationship("AcademicYear", backref=db.backref("terms", cascade="all, delete-orphan"))
    __table_args__ = (db.UniqueConstraint("academic_year_id", "name", name="uq_term_year_name"),)
