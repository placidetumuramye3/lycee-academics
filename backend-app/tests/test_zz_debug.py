def test_debug_admin(app, client):
    from app.models import User
    from app.extensions import db
    from app.routes import welfare as wf

    admin = User(username="admin_w", full_name="Admin W", password_hash="x", role="master_admin", is_active_account=True)
    db.session.add(admin)
    db.session.commit()
    with client.session_transaction() as session:
        session["_user_id"] = str(admin.id)
        session["_fresh"] = True
    view = app.view_functions["welfare_admin"]
    print("VIEW:", view, view.__dict__)
    import inspect
    print("CLOSURE:", [c.cell_contents for c in (view.__closure__ or ())])
    base = app.view_functions.get("welfare")
    print("BASE 'welfare' CLOSURE:", [c.cell_contents for c in (base.__closure__ or ())])
    print("wf.welfare_admin:", wf.welfare_admin)
    resp = client.get("/welfare/admin")
    print("ADMIN STATUS:", resp.status_code)
