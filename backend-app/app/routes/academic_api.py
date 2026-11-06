"""JSON API for cascading academic selections.

Every dropdown in the application must load its options from these
endpoints so that departments, trades, levels, classes, and modules stay
relationally consistent everywhere. All endpoints are login-protected.
"""
from flask import jsonify, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.services.academic_catalog import (
    get_departments, get_trades_by_department, get_levels_by_department,
    get_levels_by_trade, get_classes_by_trade, get_classes_by_level,
    get_modules_by_trade, get_modules_by_department, get_modules_by_class,
    get_class_context, full_structure, get_trade, get_class,
    AcademicValidationError, validate_placement,
    create_module, update_module, delete_module, serialize_module,
)
from app.models.academic_structure import AcademicModule
from app.utils.decorators import role_required
from app.utils.constants import ROLE_ACCESS

# Roles allowed to maintain the module catalog (mirrors the page permissions).
MODULE_EDITOR_ROLES = tuple(sorted(ROLE_ACCESS["classes_modules_edit"]))


def _module_payload():
    """Read module fields from a JSON body or an HTML form post."""
    payload = request.get_json(silent=True)
    if payload is None:
        payload = request.form.to_dict()
    return payload or {}


def _id(name):
    value = request.args.get(name, type=int)
    return value


def _serialize(entity, extra=None):
    payload = {"id": entity.id, "name": entity.name}
    if getattr(entity, "code", None):
        payload["code"] = entity.code
    if extra:
        payload.update(extra)
    return payload


def register_routes(app):
    @app.route("/api/academics/departments", endpoint="api_academics_departments",
               methods=["GET"])
    @login_required
    def api_departments():
        return jsonify([_serialize(d) for d in get_departments()])

    @app.route("/api/academics/trades", endpoint="api_academics_trades", methods=["GET"])
    @login_required
    def api_trades():
        department_id = _id("department_id")
        if not department_id:
            abort(400, description="A department_id query parameter is required.")
        return jsonify([_serialize(t) for t in get_trades_by_department(department_id)])

    @app.route("/api/academics/levels", endpoint="api_academics_levels", methods=["GET"])
    @login_required
    def api_levels():
        department_id = _id("department_id")
        trade_id = _id("trade_id")
        if trade_id:
            return jsonify(get_levels_by_trade(trade_id))
        if department_id:
            return jsonify(get_levels_by_department(department_id))
        abort(400, description="A department_id or trade_id query parameter is required.")

    @app.route("/api/academics/classes", endpoint="api_academics_classes", methods=["GET"])
    @login_required
    def api_classes():
        trade_id = _id("trade_id")
        department_id = _id("department_id")
        level = (request.args.get("level") or "").strip() or None
        if trade_id:
            classes = get_classes_by_trade(trade_id, level)
        elif department_id:
            classes = get_classes_by_level(department_id=department_id, level=level)
        else:
            abort(400, description="A trade_id or department_id query parameter is required.")
        return jsonify([
            _serialize(c, extra={"level": c.level, "section": c.section})
            for c in classes
        ])

    @app.route("/api/academics/modules", endpoint="api_academics_modules", methods=["GET"])
    @login_required
    def api_modules():
        class_id = _id("class_id")
        trade_id = _id("trade_id")
        department_id = _id("department_id")
        level = (request.args.get("level") or "").strip() or None
        if class_id:
            modules = get_modules_by_class(class_id)
        elif trade_id:
            modules = get_modules_by_trade(trade_id, level)
        elif department_id:
            modules = get_modules_by_department(department_id, level)
        else:
            abort(400, description="A class_id, trade_id, or department_id is required.")
        return jsonify([serialize_module(m) for m in modules])

    @app.route("/api/academics/modules", endpoint="api_academics_module_create",
               methods=["POST"])
    @role_required(*MODULE_EDITOR_ROLES)
    def api_module_create():
        payload = _module_payload()
        try:
            module = create_module(
                name=payload.get("name"),
                code=payload.get("code"),
                hours=payload.get("hours"),
                periods=payload.get("periods"),
                weight=payload.get("weight"),
                category=payload.get("category"),
                department_id=payload.get("department_id") or None,
                trade_id=payload.get("trade_id") or None,
                level=payload.get("level") or None,
                class_id=payload.get("class_id") or None,
            )
            db.session.commit()
        except AcademicValidationError as error:
            db.session.rollback()
            return jsonify({"ok": False, "message": str(error)}), 400
        return jsonify({"ok": True, "message": "Module added.",
                        "module": serialize_module(module)}), 201

    @app.route("/api/academics/modules/<int:module_id>",
               endpoint="api_academics_module_update", methods=["PUT", "PATCH"])
    @role_required(*MODULE_EDITOR_ROLES)
    def api_module_update(module_id):
        payload = _module_payload()
        try:
            module = update_module(module_id, **{
                key: payload.get(key) for key in (
                    "name", "code", "hours", "periods", "weight", "category",
                    "department_id", "trade_id", "level", "class_id")
            })
            db.session.commit()
        except AcademicValidationError as error:
            db.session.rollback()
            return jsonify({"ok": False, "message": str(error)}), 400
        return jsonify({"ok": True, "message": "Module updated.",
                        "module": serialize_module(module)})

    @app.route("/api/academics/modules/<int:module_id>",
               endpoint="api_academics_module_delete", methods=["DELETE"])
    @role_required(*MODULE_EDITOR_ROLES)
    def api_module_delete(module_id):
        try:
            delete_module(module_id)
            db.session.commit()
        except AcademicValidationError as error:
            db.session.rollback()
            return jsonify({"ok": False, "message": str(error)}), 404
        return jsonify({"ok": True, "message": "Module removed."})

    @app.route("/api/academics/class-context", endpoint="api_academics_class_context",
               methods=["GET"])
    @login_required
    def api_class_context():
        class_id = _id("class_id")
        if not class_id:
            abort(400, description="A class_id query parameter is required.")
        department, trade, klass = get_class_context(class_id)
        if not klass:
            abort(404, description="Class not found.")
        return jsonify({
            "class": _serialize(klass, extra={"level": klass.level, "section": klass.section}),
            "trade": _serialize(trade) if trade else None,
            "department": _serialize(department) if department else None,
            "modules": [serialize_module(m) for m in get_modules_by_class(class_id)],
        })

    @app.route("/api/academics/structure", endpoint="api_academics_structure",
               methods=["GET"])
    @login_required
    def api_structure():
        """One-round-trip nested structure for offline cascading dropdowns."""
        return jsonify(full_structure())

    @app.route("/api/academics/validate-placement", endpoint="api_academics_validate_placement",
               methods=["POST"])
    @login_required
    def api_validate_placement():
        payload = request.get_json(silent=True) or {}
        try:
            department, trade, level, class_name = validate_placement(
                payload.get("trade"), payload.get("level"), payload.get("class_name"))
        except AcademicValidationError as error:
            return jsonify({"valid": False, "message": str(error)}), 400
        return jsonify({"valid": True, "department": department, "trade": trade,
                        "level": level, "class_name": class_name})
