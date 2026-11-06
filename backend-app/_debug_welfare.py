from app import create_app
from app.extensions import db
from app.models import User
from app.utils.constants import ROLE_ACCESS
from app.routes import welfare as wf
from tests.conftest import TestConfig

app = create_app(TestConfig)
with app.app_context():
    db.create_all()
    admin = User(username="admin_w", full_name="Admin W", password_hash="x", role="master_admin", is_active_account=True)
    patron = User(username="patron_w", full_name="Patron W", password_hash="x", role="patron", gender="male", is_active_account=True)
    girl = User(username="girl_x", full_name="Girl X", password_hash="x", role="student", gender="female", sdms_code="SDMS-GIRL", is_active_account=True)
    db.session.add_all([admin, patron, girl])
    db.session.commit()
    print("ROLE_ACCESS welfare_admin:", ROLE_ACCESS.get("welfare_admin"))
    client = app.test_client()
    with client.session_transaction() as s:
        s["_user_id"] = str(patron.id)
        s["_fresh"] = True
    resp = client.get("/welfare/admin")
    print("ADMIN STATUS for patron:", resp.status_code)
    parent = wf.permission_for("welfare_admin")(wf.login_required(wf.welfare_admin))
    print("view func:", parent.__module__, getattr(parent, "view_class", None))
    print("wrapped:", parent.__wrapped__ if hasattr(parent, "__wrapped__") else None)
