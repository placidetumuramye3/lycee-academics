import pytest
from app.extensions import db
from app.models import User, AcademicSubject
from app.models.academic_structure import AcademicModule
from tests.test_academic_cascade import seeded_app, seeded_client

def staff_form(data, **overrides):
    form = {
        'action': 'create_staff', 'username': 'module_teacher',
        'full_name': 'Module Teacher', 'password': 'password123', 'role': 'teacher',
        'assignment_trade[]': data['trade'].name,
        'assignment_level[]': 'L3',
        'assignment_class[]': data['class'].name,
        'assignment_subject[]': data['module'].name,
    }
    form.update(overrides)
    return form

def test_staff_dropdown_uses_database_modules(seeded_client):
    client, data = seeded_client
    response = client.get('/admin')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'assignment-subject' in html
    assert 'Develop Website' in html
    assert 'SWDWD301 - Develop Website' in html
    assert 'general-course-subjects' not in html
    assert 'js/staff-assignments.js' in html

def test_create_teacher_with_catalogue_module(seeded_client):
    client, data = seeded_client
    response = client.post('/admin', data=staff_form(data))
    assert response.status_code == 302
    teacher = User.query.filter_by(username='module_teacher').one()
    assignment = AcademicSubject.query.filter_by(teacher_id=teacher.id).one()
    assert (assignment.trade, assignment.level, assignment.class_name, assignment.subject) == (
        data['trade'].name, 'L3', data['class'].name, data['module'].name)

@pytest.mark.parametrize('invalid', [
    {'assignment_subject[]': 'Made up subject'},
    {'assignment_level[]': 'L5'},
    {'assignment_class[]': 'L3 Fashion Design'},
])
def test_reject_unrelated_assignment(seeded_client, invalid):
    client, data = seeded_client
    client.post('/admin', data=staff_form(data, **invalid))
    assert User.query.filter_by(username='module_teacher').first() is None

def test_reject_module_from_other_trade_or_level(seeded_client):
    client, data = seeded_client
    for trade, level in [(data['trade2'], 'L3'), (data['trade'], 'L5')]:
        module = AcademicModule(trade_id=trade.id, level=level, name=f'Other {level}')
        db.session.add(module)
        db.session.commit()
        client.post('/admin', data=staff_form(data, **{'assignment_subject[]': module.name}))
        assert User.query.filter_by(username='module_teacher').first() is None
@pytest.mark.parametrize('entity', ['module', 'class', 'trade', 'dept'])
def test_inactive_catalogue_records_rejected(seeded_client, entity):
    client, data = seeded_client
    data[entity].is_active = False
    db.session.commit()
    client.post('/admin', data=staff_form(data))
    assert User.query.filter_by(username='module_teacher').first() is None

def test_assignment_names_are_case_insensitive(seeded_client):
    client, data = seeded_client
    client.post('/admin', data=staff_form(data, **{
        'assignment_trade[]': data['trade'].name.lower(),
        'assignment_level[]': 'l3',
        'assignment_class[]': data['class'].name.upper(),
        'assignment_subject[]': data['module'].name.lower(),
    }))
    teacher = User.query.filter_by(username='module_teacher').one()
    assert AcademicSubject.query.filter_by(teacher_id=teacher.id).one().subject == data['module'].name

def test_existing_teacher_conflict_preserved(seeded_client):
    client, data = seeded_client
    client.post('/admin', data=staff_form(data))
    client.post('/admin', data=staff_form(data, username='second_teacher'))
    assert User.query.filter_by(username='second_teacher').first() is None
