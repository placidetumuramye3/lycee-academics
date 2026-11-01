import os
import calendar
import datetime
import json
from flask import request, redirect, url_for, flash, jsonify, abort, send_file, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from markupsafe import escape
from app.extensions import db
from app.models import User, Attendance, PendingCard, FeeTransaction, FeeRequirement, Book, BookLoan, DisciplineCase, SchoolMessage, Grade, TimetableEntry, DayScheduleEntry, Setting, Assessment, AssessmentSubmission, AdmissionApplicant, Appointment, UserNotification, ActivityLog, Meeting
from app.utils.constants import *
from app.utils.decorators import role_required
from app.utils.helpers import get_setting, set_setting, attendance_for_student
from app.utils.rendering import page

from app.utils.helpers import guardian_can_access_student, linked_children
from app.utils.decorators import permission_for


def _admin_ring_svg(percent, color):
    pct = max(0, min(100, int(percent or 0)))
    return (
        f"<svg class='admin-ring' viewBox='0 0 36 36' aria-hidden='true'>"
        f"<path class='admin-ring-bg' d='M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831'/>"
        f"<path class='admin-ring-fg' stroke='{color}' stroke-dasharray='{pct}, 100' "
        f"d='M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831'/>"
        f"<text x='18' y='21' text-anchor='middle' class='admin-ring-text'>{pct}%</text></svg>"
    )


def _admin_month_calendar(today, event_days):
    weeks = calendar.monthcalendar(today.year, today.month)
    weekday_labels = "".join(f"<span>{label}</span>" for label in ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"))
    cells = []
    for week in weeks:
        for day in week:
            if day == 0:
                cells.append("<span class='admin-cal-day is-empty'></span>")
                continue
            classes = ["admin-cal-day"]
            if day == today.day:
                classes.append("is-today")
            if day in event_days:
                classes.append("has-event")
            cells.append(f"<span class='{' '.join(classes)}'>{day}</span>")
    return (
        f"<div class='admin-cal-weekdays'>{weekday_labels}</div>"
        f"<div class='admin-cal-grid'>{''.join(cells)}</div>"
    )


def _admin_pair_lists(rows, blank="Not specified", limit=8):
    labels = [(label or blank) for label, _count in rows[:limit]]
    values = [int(count) for _label, count in rows[:limit]]
    return labels, values


def _admin_rate_bars(items, accent="#2563eb"):
    if not items:
        return "<p class='admin-empty mb-0'>No records available yet.</p>"
    maximum = max((percent for _label, percent in items), default=1) or 1
    rows = []
    for label, percent in items:
        width = max(4, round(percent / maximum * 100)) if maximum else 0
        rows.append(
            f"<div class='admin-rate-row'><div class='admin-rate-label'>{escape(label)}</div>"
            f"<div class='admin-rate-track'><span style='width:{width}%;background:{accent}'></span></div>"
            f"<strong>{percent:.1f}%</strong></div>"
        )
    return "".join(rows)


def _admin_age_buckets(today):
    buckets = [("Under 15", 0), ("15-17", 0), ("18-20", 0), ("21+", 0)]
    counts = {label: 0 for label, _ in buckets}
    unknown = 0
    students = User.query.filter_by(role="student").with_entities(User.date_of_birth).all()
    for (dob,) in students:
        if not dob:
            unknown += 1
            continue
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 15:
            counts["Under 15"] += 1
        elif age <= 17:
            counts["15-17"] += 1
        elif age <= 20:
            counts["18-20"] += 1
        else:
            counts["21+"] += 1
    labels = [label for label, _ in buckets]
    values = [counts[label] for label in labels]
    if unknown:
        labels.append("Unknown")
        values.append(unknown)
    ages = [
        today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        for (dob,) in students if dob
    ]
    avg_age = round(sum(ages) / len(ages), 1) if ages else 0
    return labels, values, avg_age


def _office_activity_svg(labels, attendance, student_activity):
    left, right, top, bottom = 48, 620, 20, 196
    maximum = max(1, *attendance, *student_activity)
    grid = "".join(
        f"<line x1='{left}' y1='{top + (bottom - top) * index / 4}' x2='{right}' y2='{top + (bottom - top) * index / 4}' stroke='currentColor' stroke-opacity='.12'/><text x='{left - 10}' y='{top + (bottom - top) * index / 4 + 4}' text-anchor='end' fill='currentColor' font-size='11'>{round(maximum * (4 - index) / 4)}</text>"
        for index in range(5)
    )
    label_markup = "".join(
        f"<text class='activity-label' x='{left + (right - left) * index / max(1, len(labels) - 1)}' y='{bottom + 22}' text-anchor='middle' fill='currentColor' font-size='10'>{label}</text>"
        for index, label in enumerate(labels)
    )
    series_markup = []
    for series_id, values, color in (
        ("attendance", attendance, "#0b9b70"),
        ("student-changes", student_activity, "#d9ad2b"),
    ):
        points = [
            (left + (right - left) * index / max(1, len(values) - 1), bottom - (bottom - top) * value / maximum)
            for index, value in enumerate(values)
        ]
        point_string = " ".join(f"{x},{y}" for x, y in points)
        circles = "".join(f"<circle cx='{x}' cy='{y}' r='4' fill='{color}'/>" for x, y in points)
        series_markup.append(f"<polyline id='series-{series_id}' points='{point_string}' fill='none' stroke='{color}' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/><g id='points-{series_id}'>{circles}</g>")
    return (
        f"<svg id='secretaryActivityChartSvg' viewBox='0 0 640 250' role='img' aria-label='Attendance and student activity during the last seven days' style='width:100%;height:100%;color:var(--muted)'>"
        f"{grid}{series_markup[0]}{series_markup[1]}{label_markup}"
        "<circle cx='55' cy='240' r='4' fill='#0b9b70'/><text x='64' y='244' fill='currentColor' font-size='11'>Attendance</text>"
        "<circle cx='210' cy='240' r='4' fill='#d9ad2b'/><text x='219' y='244' fill='currentColor' font-size='11'>Student changes</text></svg>"
    )


def dashboard():
    role = current_user.role
    if role == "master_admin":
        today = datetime.date.today()
        today_iso = today.isoformat()
        month_start = today.replace(day=1)
        month_end = (month_start.replace(month=12, day=31) if today.month == 12
                     else month_start.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1))
        total_students = User.query.filter_by(role="student").count()
        total_teachers = User.query.filter_by(role="teacher").count()
        total_accounts = User.query.count()
        today_attendance = Attendance.query.filter_by(day=today_iso).count()
        pending_cards = PendingCard.query.filter_by(state="Pending").count()
        present_today = Attendance.query.filter_by(day=today_iso, status="Present").count()
        absent_today = Attendance.query.filter_by(day=today_iso, status="Absent").count()
        late_today = Attendance.query.filter_by(day=today_iso, status="Late").count()
        present_like = present_today + late_today
        active_pct = round(present_like / total_students * 100) if total_students else 0
        inactive_pct = round(absent_today / total_students * 100) if total_students else 0
        staff_count = User.query.filter(User.role.notin_(("student", "parent"))).count()
        teacher_pct = round(total_teachers / staff_count * 100) if staff_count else 0

        total_admissions = AdmissionApplicant.query.count()
        pending_admissions = AdmissionApplicant.query.filter(
            AdmissionApplicant.status.in_({"Submitted", "Under Review"})
        ).count()
        admissions_ring = round(pending_admissions / total_admissions * 100) if total_admissions else 0

        schedule_month = DayScheduleEntry.query.filter(
            DayScheduleEntry.schedule_date >= month_start,
            DayScheduleEntry.schedule_date <= month_end,
            DayScheduleEntry.is_published.is_(True),
        ).all()
        meetings_month = Meeting.query.filter(
            Meeting.scheduled_date >= month_start.isoformat(),
            Meeting.scheduled_date <= month_end.isoformat(),
            Meeting.status.in_({"Scheduled", "Rescheduled", "In Progress"}),
        ).all()
        event_days = {entry.schedule_date.day for entry in schedule_month}
        for meeting in meetings_month:
            try:
                event_days.add(datetime.date.fromisoformat(meeting.scheduled_date).day)
            except ValueError:
                pass
        upcoming_events = DayScheduleEntry.query.filter(
            DayScheduleEntry.schedule_date >= today,
            DayScheduleEntry.is_published.is_(True),
        ).count() + Meeting.query.filter(
            Meeting.scheduled_date >= today_iso,
            Meeting.status.in_({"Scheduled", "Rescheduled", "In Progress"}),
        ).count()
        events_ring = min(100, round(len(event_days) / max(1, month_end.day) * 100))

        finance_labels = []
        finance_income = []
        week_income_total = 0.0
        for days_ago in range(6, -1, -1):
            day = today - datetime.timedelta(days=days_ago)
            day_sum = db.session.query(db.func.coalesce(db.func.sum(FeeTransaction.amount), 0)).filter(
                FeeTransaction.created_at.like(f"{day.isoformat()}%")
            ).scalar()
            amount = float(day_sum or 0)
            finance_labels.append(day.strftime("%a").upper())
            finance_income.append(amount)
            week_income_total += amount

        recent_students = User.query.filter_by(role="student").order_by(User.id.desc()).limit(5).all()
        recent_students_html = "".join(
          f"<tr><td><strong>{escape(student.full_name or 'Unnamed student')}</strong></td>"
          f"<td>#{student.id}</td><td>{escape(student.class_name or 'Unassigned')}</td>"
          f"<td>{escape(student.trade or 'Not specified')}</td></tr>"
          for student in recent_students
        ) or "<tr><td class='admin-empty' colspan='4'>No students registered yet.</td></tr>"
        calendar_html = _admin_month_calendar(today, event_days)
        events_ring_svg = _admin_ring_svg(events_ring, "#ff4c61")
        admissions_ring_svg = _admin_ring_svg(admissions_ring, "#8b5cf6")
        month_label = today.strftime("%B %Y")

        body = """
<style>
.admin-dash{--ad-purple:#7c3aed;--ad-blue:#1d4ed8;--ad-pink:#ff4c61;--ad-green:#22c55e;--ad-orange:#f97316;--ad-soft:#f4f6fb;display:grid;gap:18px}
.admin-dash-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap}
.admin-dash-heading h1{margin:6px 0 4px;font-size:clamp(1.45rem,2.2vw,1.9rem)}
.admin-dash-heading p{margin:0;color:var(--muted)}
.admin-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.admin-kpi{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:118px;padding:18px 18px 16px;border-radius:22px;text-decoration:none;color:inherit;box-shadow:0 10px 28px rgba(15,23,42,.06);border:1px solid transparent;transition:transform .18s ease,box-shadow .18s ease}
.admin-kpi:hover{transform:translateY(-2px);box-shadow:0 14px 34px rgba(15,23,42,.1);color:inherit}
.admin-kpi-copy{min-width:0}
.admin-kpi-label{font-size:.78rem;font-weight:700;opacity:.86;margin-bottom:8px}
.admin-kpi-value{font-size:clamp(1.55rem,2.4vw,2.05rem);font-weight:850;line-height:1;letter-spacing:-.03em}
.admin-kpi-note{margin-top:8px;font-size:.68rem;font-weight:650;opacity:.8}
.admin-kpi-purple{background:linear-gradient(145deg,#8b5cf6,#6d28d9);color:#fff}
.admin-kpi-blue{background:linear-gradient(145deg,#2563eb,#1e3a8a);color:#fff}
.admin-kpi-white{background:var(--card);border-color:var(--border);color:var(--text)}
.admin-kpi-white .admin-kpi-label,.admin-kpi-white .admin-kpi-note{color:var(--muted);opacity:1}
.admin-kpi-icon{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;background:rgba(255,255,255,.18);font-size:1.15rem}
.admin-kpi-white .admin-kpi-icon{background:#eef2ff;color:var(--ad-blue)}
.admin-ring{width:64px;height:64px;flex:0 0 auto}
.admin-ring-bg{fill:none;stroke:rgba(15,23,42,.08);stroke-width:3.2}
[data-theme="dark"] .admin-ring-bg{stroke:rgba(255,255,255,.12)}
.admin-ring-fg{fill:none;stroke-width:3.2;stroke-linecap:round}
.admin-ring-text{font-size:7.5px;font-weight:800;fill:var(--text)}
.admin-mid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(260px,.85fr);gap:14px}
.admin-bottom{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(180px,.55fr) minmax(220px,.75fr);gap:14px}
.admin-card{background:var(--card);border:1px solid var(--border);border-radius:22px;padding:18px 18px 16px;box-shadow:0 10px 28px rgba(15,23,42,.045)}
.admin-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}
.admin-card-head h2{margin:0;font-size:1.02rem}
.admin-card-head p{margin:4px 0 0;color:var(--muted);font-size:.78rem}
.admin-toggle{display:inline-flex;gap:6px;background:var(--ad-soft);border-radius:999px;padding:4px}
[data-theme="dark"] .admin-toggle{background:rgba(255,255,255,.06)}
.admin-toggle span{border:0;border-radius:999px;padding:5px 10px;font-size:.68rem;font-weight:750;color:var(--muted)}
.admin-toggle .is-active{background:#fff;color:var(--text);box-shadow:0 2px 8px rgba(15,23,42,.08)}
[data-theme="dark"] .admin-toggle .is-active{background:rgba(255,255,255,.12);color:#fff}
.admin-finance-stats{display:flex;flex-wrap:wrap;gap:18px;margin-bottom:8px}
.admin-finance-stats strong{display:block;font-size:1.05rem;letter-spacing:-.02em}
.admin-finance-stats small{color:var(--muted);font-size:.72rem;font-weight:700}
.admin-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.admin-dot-green{background:var(--ad-green)}.admin-dot-orange{background:var(--ad-orange)}
.admin-chart{height:220px;position:relative}
.admin-cal-weekdays,.admin-cal-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;text-align:center}
.admin-cal-weekdays{margin-bottom:8px;color:var(--muted);font-size:.68rem;font-weight:750}
.admin-cal-day{display:grid;place-items:center;min-height:34px;border-radius:12px;font-size:.78rem;font-weight:700;color:var(--text)}
.admin-cal-day.is-empty{visibility:hidden}
.admin-cal-day.has-event{background:rgba(255,76,97,.12);color:var(--ad-pink)}
.admin-cal-day.is-today{background:var(--ad-pink);color:#fff;box-shadow:0 6px 14px rgba(255,76,97,.28)}
.admin-donuts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;align-items:end}
.admin-donut{text-align:center}
.admin-donut canvas{max-width:110px;margin:0 auto}
.admin-donut strong{display:block;margin-top:6px;font-size:.95rem}
.admin-donut small{color:var(--muted);font-size:.7rem;font-weight:700}
.admin-summary{display:flex;flex-direction:column;justify-content:center;align-items:flex-start;gap:8px;min-height:180px}
.admin-summary-value{font-size:2.1rem;font-weight:850;letter-spacing:-.04em;line-height:1}
.admin-summary-trend{display:inline-flex;align-items:center;gap:6px;color:var(--ad-pink);font-weight:750;font-size:.78rem}
.admin-recent-list{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.admin-recent-list li{display:flex;align-items:center;gap:10px}
.admin-recent-list strong{display:block;font-size:.82rem}
.admin-recent-list small{color:var(--muted);font-size:.7rem}
.admin-avatar{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:linear-gradient(135deg,#8b5cf6,#2563eb);color:#fff;font-weight:800;font-size:.78rem;flex:0 0 auto}
.admin-empty{color:var(--muted);font-size:.82rem}
.admin-quick{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.admin-quick a{display:flex;align-items:center;gap:10px;padding:12px;border:1px solid var(--border);border-radius:14px;color:var(--text);background:var(--ad-soft);font-weight:700;font-size:.82rem}
[data-theme="dark"] .admin-quick a{background:rgba(255,255,255,.04)}
.admin-quick a i{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;background:#fff;color:var(--ad-blue)}
[data-theme="dark"] .admin-quick a i{background:rgba(255,255,255,.08)}
@media(max-width:1100px){.admin-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.admin-mid,.admin-bottom{grid-template-columns:1fr}.admin-quick{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.admin-kpis,.admin-donuts,.admin-quick{grid-template-columns:1fr}.admin-kpi{min-height:98px}.admin-chart{height:190px}}
.admin-dash{--ad-green:#169b72;--ad-orange:#e59b52;--ad-blue:#468f85;--ad-soft:#f2f7f4;gap:14px}
.admin-dash-heading{padding:22px 24px;border-radius:12px;background:linear-gradient(110deg,#e9c18e 0%,#f2e7d5 45%,#6e9f87 100%);align-items:center}
.admin-dash-heading h1{font-size:1.35rem;font-weight:750;color:#183c34;margin:5px 0}
.admin-dash-heading p{color:#36594e;font-size:.82rem}
.admin-dash-heading .pill{background:rgba(255,255,255,.55);color:#36594e}
.admin-dash-heading .btn{background:#fff;color:#345d50;border:0}
.admin-kpis{gap:10px}
.admin-kpi{min-height:90px;padding:13px 15px;border-radius:12px;box-shadow:none}
.admin-kpi-purple{background:#fff1e8;color:#654a39}.admin-kpi-blue{background:#e8f4ef;color:#245a4a}
.admin-kpi-white{background:var(--card);border-color:var(--border)}
.admin-kpi-icon{width:34px;height:34px;border-radius:10px;background:rgba(255,255,255,.72);color:#178867}
.admin-kpi-purple .admin-kpi-icon{color:#d79054}.admin-kpi-blue .admin-kpi-icon{color:#358c72}
.admin-card{border-radius:12px;padding:15px;box-shadow:none}
.admin-card-head h2{font-size:.92rem}
.admin-bottom{grid-template-columns:minmax(0,1.15fr) minmax(160px,.55fr) minmax(0,1fr)}
.admin-academic-table{width:100%;border-collapse:collapse;min-width:500px}
.admin-academic-table th{padding:9px 10px;text-align:left;color:var(--muted);font-size:.66rem;font-weight:750;border-bottom:1px solid var(--border)}
.admin-academic-table td{padding:10px;border-bottom:1px solid var(--border);font-size:.75rem}
.admin-academic-table tr:last-child td{border-bottom:0}
.admin-academic-table td:first-child strong{font-weight:750}
.admin-academic-table-wrap{overflow-x:auto}
@media(max-width:900px){.admin-bottom{grid-template-columns:1fr}.admin-dash-heading{align-items:flex-start}}
@media(max-width:600px){.admin-dash-heading{padding:17px}.admin-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.admin-kpi{min-width:0;padding:11px}.admin-kpi-value{font-size:1.45rem}}
</style>
<div class="admin-dash">
  <div class="admin-dash-heading">
    <div>
      <span class="pill">{{ month_label }} · SCHOOL OVERVIEW</span>
      <h1>Overall Student Performance Dashboard</h1>
      <p>Attendance, enrollment, and school activity at a glance.</p>
    </div>
    <a class="btn btn-accent" href="/admin"><i class="bi bi-arrow-up-right me-1"></i> Get Access</a>
  </div>

  <section class="admin-kpis" aria-label="Key metrics">
    <a class="admin-kpi admin-kpi-purple" href="/students">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Total Students</div>
        <div class="admin-kpi-value">{{ total_students }}</div>
        <div class="admin-kpi-note">{{ total_accounts }} system accounts</div>
      </div>
      <span class="admin-kpi-icon"><i class="bi bi-people-fill"></i></span>
    </a>
    <a class="admin-kpi admin-kpi-blue" href="/admin">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Total Teachers</div>
        <div class="admin-kpi-value">{{ total_teachers }}</div>
        <div class="admin-kpi-note">Teacher accounts</div>
      </div>
      <span class="admin-kpi-icon"><i class="bi bi-mortarboard-fill"></i></span>
    </a>
    <a class="admin-kpi admin-kpi-white" href="/day-schedule">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Events</div>
        <div class="admin-kpi-value">{{ upcoming_events }}</div>
        <div class="admin-kpi-note">Upcoming schedules & meetings</div>
      </div>
      {{ events_ring_svg|safe }}
    </a>
    <a class="admin-kpi admin-kpi-white" href="/admissions">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Admissions</div>
        <div class="admin-kpi-value">{{ total_admissions }}</div>
        <div class="admin-kpi-note">{{ pending_admissions }} pending review</div>
      </div>
      {{ admissions_ring_svg|safe }}
    </a>
  </section>

  <div class="admin-mid">
    <section class="admin-card">
      <div class="admin-card-head">
        <div>
          <h2>School Finance</h2>
          <p>Fee payments recorded during the last 7 days.</p>
        </div>
        <div class="admin-toggle" aria-hidden="true"><span>Monthly</span><span class="is-active">Weekly</span></div>
      </div>
      <div class="admin-finance-stats">
        <div><small><span class="admin-dot admin-dot-green"></span>Income</small><strong>{{ week_income_display }} RWF</strong></div>
        <div><small><span class="admin-dot admin-dot-orange"></span>Expense</small><strong>0 RWF</strong></div>
      </div>
      <div class="admin-chart"><canvas id="adminFinanceChart"></canvas></div>
    </section>
    <section class="admin-card">
      <div class="admin-card-head">
        <div>
          <h2>School Event Calendar</h2>
          <p>{{ month_label }}</p>
        </div>
        <a href="/meetings" class="btn btn-sm btn-outline-success">Meetings</a>
      </div>
      {{ calendar_html|safe }}
    </section>
  </div>

  <div class="admin-bottom">
    <section class="admin-card">
      <div class="admin-card-head">
        <div>
          <h2>Attendance Snapshot</h2>
          <p>Today’s present, absent, and teacher share of staff.</p>
        </div>
        <span class="pill">{{ today_iso }}</span>
      </div>
      <div class="admin-donuts">
        <div class="admin-donut"><canvas id="adminActiveChart"></canvas><strong>{{ active_pct }}%</strong><small>Present / Late</small></div>
        <div class="admin-donut"><canvas id="adminInactiveChart"></canvas><strong>{{ inactive_pct }}%</strong><small>Absent</small></div>
        <div class="admin-donut"><canvas id="adminTeacherChart"></canvas><strong>{{ teacher_pct }}%</strong><small>Teachers of staff</small></div>
      </div>
    </section>
    <section class="admin-card admin-summary">
      <small class="muted" style="font-weight:750">Admission Summary</small>
      <div class="admin-summary-value">{{ total_admissions }}</div>
      <div class="admin-summary-trend"><i class="bi bi-arrow-down-right"></i> {{ pending_admissions }} awaiting review</div>
      <a class="btn btn-sm btn-accent mt-2" href="/admissions">Open admissions</a>
    </section>
    <section class="admin-card">
      <div class="admin-card-head">
        <div>
          <h2>Recently Registered Students</h2>
          <p>Latest student records by class and trade.</p>
        </div>
        <a href="/students" class="btn btn-sm btn-outline-success">View all</a>
      </div>
      <div class="admin-academic-table-wrap">
        <table class="admin-academic-table">
          <thead><tr><th>Name</th><th>Student ID</th><th>Class</th><th>Trade</th></tr></thead>
          <tbody>{{ recent_students_html|safe }}</tbody>
        </table>
      </div>
    </section>
  </div>

  <section class="admin-card">
    <div class="admin-card-head">
      <div>
        <h2>Quick Access</h2>
        <p>Open the most-used school modules. Pending RFID cards: {{ pending_cards }}.</p>
      </div>
    </div>
    <div class="admin-quick">
      <a href="/students"><i class="bi bi-people"></i><span>Students</span></a>
      <a href="/grades"><i class="bi bi-journal-text"></i><span>Report Cards</span></a>
      <a href="/fees"><i class="bi bi-cash-stack"></i><span>Fees</span></a>
      <a href="/timetable"><i class="bi bi-calendar3"></i><span>Timetable</span></a>
      <a href="/school-structure"><i class="bi bi-diagram-3"></i><span>School Structure</span></a>
    </div>
  </section>
</div>
<script>
(() => {
  const muted = getComputedStyle(document.documentElement).getPropertyValue('--muted').trim() || '#667085';
  const financeLabels = {{ finance_labels|safe }};
  const financeIncome = {{ finance_income|safe }};
  const commonDonut = (el, value, color) => {
    if (!el || !window.Chart) return;
    new Chart(el, {
      type: 'doughnut',
      data: { labels: ['Value', 'Rest'], datasets: [{ data: [value, Math.max(0, 100 - value)], backgroundColor: [color, 'rgba(148,163,184,.18)'], borderWidth: 0 }] },
      options: { responsive: true, maintainAspectRatio: true, cutout: '72%', plugins: { legend: { display: false }, tooltip: { enabled: false } } }
    });
  };
  if (window.Chart) {
    new Chart(document.getElementById('adminFinanceChart'), {
      type: 'line',
      data: {
        labels: financeLabels,
        datasets: [
          { label: 'Income', data: financeIncome, borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,.12)', fill: true, tension: .38, pointRadius: 4, pointHoverRadius: 6 },
          { label: 'Expense', data: financeLabels.map(() => 0), borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,.08)', fill: false, tension: .38, pointRadius: 3 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { color: muted, callback: (v) => Number(v).toLocaleString() }, grid: { color: 'rgba(120,135,140,.12)' } },
          x: { ticks: { color: muted }, grid: { display: false } }
        }
      }
    });
    commonDonut(document.getElementById('adminActiveChart'), {{ active_pct }}, '#ff4c61');
    commonDonut(document.getElementById('adminInactiveChart'), {{ inactive_pct }}, '#8b5cf6');
    commonDonut(document.getElementById('adminTeacherChart'), {{ teacher_pct }}, '#2563eb');
  }
})();
</script>
"""
        return page(
            "Analytics Dashboard",
            body,
            "master_admin",
            total_accounts=total_accounts,
            total_students=total_students,
            total_teachers=total_teachers,
            today_attendance=today_attendance,
            pending_cards=pending_cards,
            today_iso=today_iso,
            upcoming_events=upcoming_events,
            total_admissions=total_admissions,
            pending_admissions=pending_admissions,
            week_income_total=week_income_total,
            week_income_display=f"{week_income_total:,.0f}",
            month_label=month_label,
            active_pct=active_pct,
            inactive_pct=inactive_pct,
            teacher_pct=teacher_pct,
            events_ring_svg=events_ring_svg,
            admissions_ring_svg=admissions_ring_svg,
            calendar_html=calendar_html,
            recent_students_html=recent_students_html,
            finance_labels=json.dumps(finance_labels),
            finance_income=json.dumps(finance_income),
        )
    if role == "head_teacher":
        student_count = User.query.filter_by(role="student").count()
        teacher_count = User.query.filter_by(role="teacher").count()
        today_count = Attendance.query.filter_by(day=datetime.date.today().isoformat()).count()
        case_count = DisciplineCase.query.count()
        return page("Head Teacher Dashboard", f"""<div class='dashboard-heading'><div><span class='pill'>SCHOOL LEADERSHIP</span><h1 class='mt-2'>Welcome, <span class='accent'>{current_user.full_name}</span></h1><p>School-wide overview of students, teaching staff, attendance, academics, and discipline.</p></div></div><section class='grid mb-4'><div class='stat'><div class='stat-value'>{student_count}</div><div class='stat-label'>Students</div></div><div class='stat'><div class='stat-value'>{teacher_count}</div><div class='stat-label'>Teachers</div></div><div class='stat'><div class='stat-value'>{today_count}</div><div class='stat-label'>Attendance records today</div></div><div class='stat'><div class='stat-value'>{case_count}</div><div class='stat-label'>Discipline cases</div></div></section><section class='panel'><h2>School Oversight</h2><p class='muted'>Review school activity and support teachers and students across academic and discipline matters.</p><div class='d-flex gap-2 flex-wrap'><a class='btn btn-accent' href='/academic-management'>Academic Management</a><a class='btn btn-outline-success' href='/students'>Students</a><a class='btn btn-outline-success' href='/attendance'>Attendance</a><a class='btn btn-outline-success' href='/grades'>Examination Results</a><a class='btn btn-outline-success' href='/assessments'>Assignments & Assessments</a><a class='btn btn-outline-success' href='/discipline'>Discipline Reports</a><a class='btn btn-outline-success' href='/timetable'>Timetables</a></div></section>""", "head_teacher")
    if role == "teacher":
        students_count=User.query.filter_by(role="student").count(); attendance_count=Attendance.query.filter_by(day=datetime.date.today().isoformat()).count(); grades_count=Grade.query.filter_by(teacher_id=current_user.id).count()
        assigned_assessments = Assessment.query.filter_by(teacher_id=current_user.id, is_published=True).all()
        assigned_total = completed_total = 0
        graded_percentages = []
        for assessment in assigned_assessments:
            if assessment.target_student_ids:
                try:
                    target_ids = {int(value) for value in json.loads(assessment.target_student_ids)}
                except (TypeError, ValueError, json.JSONDecodeError):
                    target_ids = set()
                assigned_students = User.query.filter(
                    User.id.in_(target_ids), User.role == "student", User.class_name == assessment.class_name
                ).all() if target_ids else []
            else:
                assigned_students = User.query.filter_by(role="student", class_name=assessment.class_name).all()
            assigned_ids = {student.id for student in assigned_students}
            assigned_total += len(assigned_ids)
            submissions = AssessmentSubmission.query.filter_by(assessment_id=assessment.id).all()
            visible_submissions = [submission for submission in submissions if submission.student_id in assigned_ids]
            completed_total += len(visible_submissions)
            if assessment.max_score > 0:
                graded_percentages.extend(
                    submission.score / assessment.max_score * 100 for submission in visible_submissions
                    if submission.is_graded and submission.score is not None)
        completion_rate = f"{completed_total / assigned_total * 100:.0f}%" if assigned_total else "—"
        average_assessment_grade = f"{sum(graded_percentages) / len(graded_percentages):.1f}%" if graded_percentages else "—"
        body=f"""<div class='dashboard-heading'><div><span class='pill'>TEACHER WORKSPACE</span><h1 class='mt-2'>Welcome, <span class='accent'>{current_user.full_name}</span></h1><p>Manage attendance, students, timetables and academic records.</p></div></div><section class='grid mb-4'><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-people'></i></span></div><div class='stat-value'>{students_count}</div><div class='stat-label'>Students</div></div><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-calendar-check'></i></span></div><div class='stat-value'>{attendance_count}</div><div class='stat-label'>Attendance records today</div></div><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-journal-check'></i></span></div><div class='stat-value'>{grades_count}</div><div class='stat-label'>Grades entered by you</div></div><a class='stat text-decoration-none' href='/assessments'><div class='stat-top'><span class='stat-icon'><i class='bi bi-clipboard-data'></i></span></div><div class='stat-value'>{completion_rate}</div><div class='stat-label'>Assessment completion</div><div class='stat-note'>Average graded score: {average_assessment_grade}</div></a></section><section class='panel'><h2>Quick Actions</h2><div class='row g-3 mt-1'><div class='col-md-3'><a class='quick-link' href='/attendance'><i class='bi bi-calendar-check'></i><strong>Attendance</strong></a></div><div class='col-md-3'><a class='quick-link' href='/students'><i class='bi bi-people'></i><strong>Students</strong></a></div><div class='col-md-3'><a class='quick-link' href='/grades'><i class='bi bi-journal-text'></i><strong>Report Cards</strong></a></div><div class='col-md-3'><a class='quick-link' href='/timetable'><i class='bi bi-calendar3'></i><strong>Timetable</strong></a></div><div class='col-md-3'><a class='quick-link' href='/assessments'><i class='bi bi-clipboard-data'></i><strong>Assessment Analytics</strong></a></div></div></section>"""
        return page("Teacher Dashboard",body,"teacher")
    if role == "accountant":
        tx_count=FeeTransaction.query.count(); total_paid=sum((t.amount or 0) for t in FeeTransaction.query.all())
        return page("Accountant Dashboard",f"""<div class='dashboard-heading'><div><span class='pill'>FINANCE</span><h1 class='mt-2'>Fee <span class='accent'>Management</span></h1><p>Manage payments and review financial transactions saved in the system.</p></div></div><section class='grid mb-4'><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-receipt'></i></span></div><div class='stat-value'>{tx_count}</div><div class='stat-label'>Fee Transactions</div></div><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-cash-stack'></i></span></div><div class='stat-value'>{total_paid:,.0f}</div><div class='stat-label'>Total Amount Recorded (RWF)</div></div></section><section class='panel'><a class='btn btn-accent' href='/fees'><i class='bi bi-cash-stack me-1'></i> Open Fee Records</a></section>""","accountant")
    if role == "librarian":
        books=Book.query.count(); available=sum((b.available or 0) for b in Book.query.all())
        return page("Librarian Dashboard",f"""<div class='dashboard-heading'><div><span class='pill'>LIBRARY</span><h1 class='mt-2'>Library <span class='accent'>Inventory</span></h1><p>Manage books, categories, quantities and availability.</p></div></div><section class='grid mb-4'><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-book'></i></span></div><div class='stat-value'>{books}</div><div class='stat-label'>Book Titles</div></div><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-bookmark-check'></i></span></div><div class='stat-value'>{available}</div><div class='stat-label'>Available Copies</div></div></section><section class='panel'><a class='btn btn-accent' href='/library'><i class='bi bi-book me-1'></i> Open Library Catalogue</a></section>""","librarian")
    if role == "discipline":
        cases=DisciplineCase.query.count(); students=User.query.filter_by(role="student").count()
        return page("Discipline Dashboard",f"""<div class='dashboard-heading'><div><span class='pill'>DISCIPLINE</span><h1 class='mt-2'>Discipline <span class='accent'>Records</span></h1><p>Record student conduct cases and review attendance.</p></div></div><section class='grid mb-4'><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-shield-check'></i></span></div><div class='stat-value'>{cases}</div><div class='stat-label'>Recorded Cases</div></div><div class='stat'><div class='stat-top'><span class='stat-icon'><i class='bi bi-people'></i></span></div><div class='stat-value'>{students}</div><div class='stat-label'>Students</div></div></section><section class='panel'><div class='d-flex gap-2 flex-wrap'><a class='btn btn-accent' href='/discipline'>Open Discipline Records</a><a class='btn btn-outline-success' href='/attendance'>View Attendance Register</a></div></section>""","discipline")
    if role == "auditor":
        return page(
            "Messaging Audit Workspace",
            "<section class='panel'><h1>Messaging <span class='accent'>Audit Workspace</span></h1><p class='muted'>Read-only access to the signed communication and moderation trail. This role cannot send messages, inspect private conversations, or issue school instructions.</p><a class='btn btn-accent' href='/messages?view=audit'>Open Messaging Audit Trail</a></section>",
            "auditor",
        )
    if role == "parent":
        children=linked_children(current_user.id); rows="".join(f"<tr><td><strong>{s.full_name}</strong></td><td>{s.class_name or '-'}</td><td>{s.level or '-'}</td><td>{s.trade or '-'}</td><td><div class='d-flex align-items-center gap-2 flex-nowrap'><a class='btn btn-sm btn-accent text-nowrap' href='/student/profile/{s.id}'>Student Profile</a><a class='btn btn-sm btn-outline-success text-nowrap' href='/parent/child/{s.id}'>View Details</a><a class='btn btn-sm btn-outline-success text-nowrap' href='/grades'>Academics</a></div></td></tr>" for s in children)
        return page("Parent Dashboard",f"""<div class='dashboard-heading'><div><span class='pill'>FAMILY PORTAL</span><h1 class='mt-2'>Family <span class='accent'>Overview</span></h1><p>Only students explicitly linked to your account are displayed here.</p></div></div><section class='panel'><div class='stat mb-4'><div class='stat-value'>{len(children)}</div><div class='stat-label'>Linked Students</div></div><div class='table-responsive'><table class='table align-middle'><thead><tr><th>Student</th><th>Class</th><th>Level</th><th>Trade</th><th>Action</th></tr></thead><tbody>{rows or '<tr><td colspan="5" class="muted">No student has been linked to your account yet.</td></tr>'}</tbody></table></div><a class='btn btn-accent mt-2' href='/timetable'><i class='bi bi-calendar3 me-1'></i> Children’s Timetables</a> <a class='btn btn-outline-success mt-2' href='/day-schedule'><i class='bi bi-calendar-event me-1'></i> Day Schedule</a> <a class='btn btn-outline-success mt-2' href='/messages'><i class='bi bi-chat-left-text me-1'></i> School Messages</a></section>""","parent")
    if role in {"secretary", "patron", "matron"}:
        titles = {"secretary": "School Office", "patron": "Patron Workspace", "matron": "Matron Workspace"}
        if role == "secretary":
            today_date = datetime.date.today()
            today = today_date.isoformat()
            student_count = User.query.filter_by(role="student").count()
            attendance_count = Attendance.query.filter_by(day=today).count()
            late_count = Attendance.query.filter_by(day=today, status="Late").count()
            pending_admissions = AdmissionApplicant.query.filter(AdmissionApplicant.status.in_({"Submitted", "Under Review"})).count()
            upcoming_appointments = Appointment.query.filter(Appointment.scheduled_date >= today, Appointment.status.in_({"Scheduled", "Rescheduled"})).count()
            unread_alerts = UserNotification.query.filter_by(user_id=current_user.id, is_read=False).count()
            trend_labels = []
            attendance_trend = []
            student_activity_trend = []
            for days_ago in range(6, -1, -1):
                date = today_date - datetime.timedelta(days=days_ago)
                date_label = date.strftime("%d %b")
                trend_labels.append(date_label)
                attendance_trend.append(Attendance.query.filter_by(day=date.isoformat()).count())
                student_activity_trend.append(ActivityLog.query.filter(
                    ActivityLog.created_at >= datetime.datetime.combine(date, datetime.time.min),
                    ActivityLog.created_at < datetime.datetime.combine(date + datetime.timedelta(days=1), datetime.time.min),
                    ActivityLog.action.in_({"Student registered", "Admission converted", "Student removed"}),
                ).count())
            recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(6).all()
            activity_rows = "".join(
                f"<tr><td>{escape(item.created_at.strftime('%d %b %Y, %H:%M'))}</td><td>{escape(item.action)}</td><td>{escape(item.student_name)}</td></tr>"
                for item in recent_activity
            )
            admission_status_counts = db.session.query(
                AdmissionApplicant.status, db.func.count(AdmissionApplicant.id)
            ).group_by(AdmissionApplicant.status).order_by(AdmissionApplicant.status).all()
            admission_status_rows = "".join(
                f"<div class='admission-status-row'><span><i></i>{escape(status)}</span><strong>{count}</strong></div>"
                for status, count in admission_status_counts
            ) or "<p class='muted mb-0'>No admission applications have been received.</p>"
            body = f"""<section class='panel hero-card'><span class='pill'>SECRETARY WORKSPACE</span><h1 class='mt-2'>Welcome back, {escape(current_user.full_name)}</h1><p class='muted'>Your school office overview for {today}.</p></section><section class='grid mb-4'><a class='stat text-decoration-none' href='/students'><div class='stat-value'>{student_count}</div><div class='stat-label'>Registered Students</div></a><a class='stat text-decoration-none' href='/attendance'><div class='stat-value'>{attendance_count}</div><div class='stat-label'>Attendance Records Today</div></a><a class='stat text-decoration-none' href='/attendance'><div class='stat-value'>{late_count}</div><div class='stat-label'>Late Arrivals Today</div></a><a class='stat text-decoration-none' href='/admissions'><div class='stat-value'>{pending_admissions}</div><div class='stat-label'>Admissions To Review</div></a><a class='stat text-decoration-none' href='/appointments'><div class='stat-value'>{upcoming_appointments}</div><div class='stat-label'>Upcoming Appointments</div></a><a class='stat text-decoration-none' href='/notifications'><div class='stat-value'>{unread_alerts}</div><div class='stat-label'>Unread Alerts</div></a></section><div class='row g-4 mb-4'><div class='col-xl-7'><section class='panel chart-card'><div class='dashboard-heading mb-2'><div><h2>Office Activity</h2><p>Daily attendance records and student additions/removals over the last 7 days.</p></div><span class='pill'>LIVE DATA</span></div><div class='chart-wrap'><canvas id='secretaryActivityChart'></canvas></div></section></div><div class='col-xl-5'><section class='panel chart-card'><div class='dashboard-heading mb-2'><div><h2>Admission Status</h2><p>Applicants by their current status.</p></div></div><div class='chart-wrap'><canvas id='secretaryAdmissionsChart'></canvas></div></section></div></div><section class='panel'><div class='dashboard-heading'><div><h2>Recent Student Activity</h2><p>Recorded registrations, removals, and student changes.</p></div><a class='btn btn-sm btn-outline-success' href='/activity-history'>View history</a></div><div class='table-responsive'><table class='table align-middle'><thead><tr><th>Date</th><th>Activity</th><th>Student</th></tr></thead><tbody>{activity_rows or "<tr><td colspan='3' class='muted'>No student activity has been recorded yet.</td></tr>"}</tbody></table></div><p class='small muted mb-0'>Charts show records currently stored and activity explicitly logged by the system.</p></section><script>const chartText=getComputedStyle(document.documentElement).getPropertyValue('--muted').trim();new Chart(document.getElementById('secretaryActivityChart'),{{type:'line',data:{{labels:{json.dumps(trend_labels)},datasets:[{{label:'Attendance records',data:{json.dumps(attendance_trend)},borderColor:'#0b9b70',backgroundColor:'rgba(11,155,112,.12)',fill:true,tension:.38}},{{label:'Student additions/removals',data:{json.dumps(student_activity_trend)},borderColor:'#d9ad2b',backgroundColor:'rgba(217,173,43,.12)',fill:true,tension:.38}}]}},options:{{responsive:true,maintainAspectRatio:false,scales:{{y:{{beginAtZero:true,ticks:{{precision:0,color:chartText}}}},x:{{ticks:{{color:chartText}}}}}}}}}});new Chart(document.getElementById('secretaryAdmissionsChart'),{{type:'doughnut',data:{{labels:{json.dumps([status for status, in db.session.query(AdmissionApplicant.status).distinct().all()])},datasets:[{{data:{json.dumps([AdmissionApplicant.query.filter_by(status=status).count() for status, in db.session.query(AdmissionApplicant.status).distinct().all()])},backgroundColor:['#0b9b70','#39bd72','#d9ad2b','#8cc63e','#7a8b85','#4f6f64'],borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,cutout:'65%',plugins:{{legend:{{position:'bottom',labels:{{color:chartText,usePointStyle:true}}}}}}}}}});</script>"""
            body += """<script>(()=>{const canvas=document.getElementById('secretaryActivityChart');if(!canvas)return;const chartCard=canvas.closest('.chart-card');const badge=chartCard.querySelector('.pill');const status=document.createElement('p');status.className='small muted mb-0 mt-2';canvas.parentElement.after(status);async function refreshActivity(){try{const response=await fetch('/dashboard/secretary-analytics',{headers:{'Accept':'application/json'}});if(!response.ok)throw new Error('Analytics refresh failed');const data=await response.json();const chart=window.Chart&&Chart.getChart(canvas);if(!chart){status.textContent='Chart library unavailable; reload the page to try again.';return}chart.data.labels=data.labels;chart.data.datasets[0].data=data.attendance;chart.data.datasets[1].data=data.student_activity;chart.update('none');status.textContent='Updated at '+data.updated_at;badge.textContent='LIVE · 30 SEC REFRESH'}catch(error){status.textContent='Live refresh unavailable; showing the last loaded data.'}}refreshActivity();window.setInterval(refreshActivity,30000)})();</script>"""
            body += """<script>(()=>{const canvas=document.getElementById('secretaryActivityChart');if(!canvas||window.Chart&&Chart.getChart(canvas))return;const wrap=canvas.parentElement;const status=wrap.nextElementSibling;const namespace='http://www.w3.org/2000/svg';let svg;function node(name,attributes={},text=''){const item=document.createElementNS(namespace,name);Object.entries(attributes).forEach(([key,value])=>item.setAttribute(key,value));if(text)item.textContent=text;return item}function draw(data){canvas.hidden=true;if(!svg){svg=node('svg',{id:'secretaryActivityFallback',viewBox:'0 0 640 250',role:'img','aria-label':'Attendance and student activity during the last seven days'});svg.style.width='100%';svg.style.height='100%';wrap.appendChild(svg)}svg.replaceChildren();const left=48,right=620,top=20,bottom=196,maximum=Math.max(1,...data.attendance,...data.student_activity);for(let index=0;index<5;index++){const y=top+(bottom-top)*index/4;svg.appendChild(node('line',{x1:left,y1:y,x2:right,y2:y,stroke:'currentColor','stroke-opacity':'.12'}));svg.appendChild(node('text',{x:left-10,y:y+4,'text-anchor':'end',fill:'currentColor','font-size':'11'},String(Math.ceil(maximum*(4-index)/4))))}[data.attendance,data.student_activity].forEach((values,series)=>{const points=values.map((value,index)=>({x:left+(right-left)*(index/Math.max(1,values.length-1)),y:bottom-(bottom-top)*value/maximum}));svg.appendChild(node('polyline',{points:points.map(point=>`${point.x},${point.y}`).join(' '),fill:'none',stroke:series?'#d9ad2b':'#0b9b70','stroke-width':'3','stroke-linecap':'round','stroke-linejoin':'round'}));points.forEach(point=>svg.appendChild(node('circle',{cx:point.x,cy:point.y,r:4,fill:series?'#d9ad2b':'#0b9b70'})))});data.labels.forEach((label,index)=>{const x=left+(right-left)*(index/Math.max(1,data.labels.length-1));svg.appendChild(node('text',{x,y:bottom+22,'text-anchor':'middle',fill:'currentColor','font-size':'10'},label))});[['Attendance','#0b9b70'],['Student changes','#d9ad2b']].forEach(([label,color],index)=>{const x=left+index*155;svg.appendChild(node('circle',{cx:x,cy:240,r:4,fill:color}));svg.appendChild(node('text',{x:x+9,y:244,fill:'currentColor','font-size':'11'},label))})}async function refresh(){try{const response=await fetch('/dashboard/secretary-analytics',{headers:{Accept:'application/json'}});if(!response.ok)throw new Error();draw(await response.json());if(status)status.textContent='Updated just now · refreshes every 30 seconds'}catch(error){if(status)status.textContent='Could not refresh analytics. Showing latest available data.'}}refresh();window.setInterval(refresh,30000)})();</script>"""
            body = body.replace("<canvas id='secretaryActivityChart'></canvas>", _office_activity_svg(trend_labels, attendance_trend, student_activity_trend))
            body = body.replace("<div class='chart-wrap'><canvas id='secretaryAdmissionsChart'></canvas></div>", f"<div class='admission-status-list'>{admission_status_rows}</div>")
            body = body.replace("<script>const chartText=", "<script>if(document.getElementById('attendanceChart')){const chartText=").replace("</script>", "}</script>")
            body = body.replace("class='panel hero-card'", "class='panel office-welcome'")
            body = body.replace("class='stat text-decoration-none'", "class='stat office-stat text-decoration-none'")
            body = body.replace("SECRETARY WORKSPACE", "SCHOOL OFFICE")
            body = body.replace("Welcome back,", "Good morning,")
            body = "<style>.office-welcome{background:linear-gradient(115deg,#e5f5ed,#e8f3fb 72%,#f6f3e8);border:1px solid #dcece4;color:#26333a;padding:18px 22px;margin-bottom:14px}.office-welcome h1{color:#26333a;font-size:clamp(1.25rem,1.8vw,1.55rem);margin:.45rem 0}.office-welcome p{font-size:.9rem;margin:0}.office-welcome .muted{color:#718087!important}.office-welcome .accent{color:#0b9b70}.office-welcome .pill{background:#fff;border-color:#d8ebe0;color:#0b8061;padding:4px 9px;font-size:.62rem}.office-stat{border:0;min-height:94px;padding:14px 16px;display:flex;flex-direction:column;justify-content:center;box-shadow:0 4px 14px rgba(28,55,47,.045)}.office-stat:nth-child(6n+1){background:#e7f4ec}.office-stat:nth-child(6n+2){background:#e8f1fb}.office-stat:nth-child(6n+3){background:#fff2df}.office-stat:nth-child(6n+4){background:#f2edfb}.office-stat:nth-child(6n+5){background:#e4f5f3}.office-stat:nth-child(6n){background:#fff0ed}.office-stat .stat-value{font-size:1.55rem;color:#26333a}.office-stat .stat-label{font-size:.75rem;font-weight:650;color:#607078;margin-top:5px}.office-dashboard-panel{border:1px solid #e7ecea;box-shadow:0 7px 24px rgba(28,55,47,.045)}.admission-status-list{display:grid;gap:10px;padding:14px 4px}.admission-status-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px;border-radius:12px;background:var(--page)}.admission-status-row span{display:flex;align-items:center;gap:10px}.admission-status-row i{width:10px;height:10px;border-radius:50%;background:#0b9b70}.admission-status-row:nth-child(3n+2) i{background:#d9ad2b}.admission-status-row:nth-child(3n) i{background:#5795d2}.office-welcome+.grid{margin-top:0}@media(max-width:600px){.office-welcome{padding:15px 16px}.office-stat{min-height:78px;padding:11px 13px}.office-stat .stat-value{font-size:1.35rem}}</style>" + body
            body += """<script>(()=>{const svg=document.getElementById('secretaryActivityChartSvg');if(!svg)return;const status=document.createElement('p');status.className='small muted mb-0 mt-2';svg.parentElement.after(status);function update(data){const left=48,right=620,top=20,bottom=196,maximum=Math.max(1,...data.attendance,...data.student_activity);[['attendance',data.attendance],['student-changes',data.student_activity]].forEach(([name,values])=>{const points=values.map((value,index)=>({x:left+(right-left)*index/Math.max(1,values.length-1),y:bottom-(bottom-top)*value/maximum}));svg.querySelector('#series-'+name).setAttribute('points',points.map(point=>point.x+','+point.y).join(' '));const group=svg.querySelector('#points-'+name);group.replaceChildren(...points.map(point=>{const circle=document.createElementNS('http://www.w3.org/2000/svg','circle');circle.setAttribute('cx',point.x);circle.setAttribute('cy',point.y);circle.setAttribute('r','4');circle.setAttribute('fill',name==='attendance'?'#0b9b70':'#d9ad2b');return circle}))});svg.querySelectorAll('.activity-label').forEach((label,index)=>{if(data.labels[index])label.textContent=data.labels[index]})}async function refresh(){try{const response=await fetch('/dashboard/secretary-analytics',{headers:{Accept:'application/json'}});if(!response.ok)throw new Error();update(await response.json());status.textContent='Live · updated just now · refreshes every 30 seconds'}catch(error){status.textContent='Could not refresh analytics; chart shows the latest loaded data.'}}refresh();window.setInterval(refresh,30000)})();</script>"""
            return page(titles[role], body, role)
        admissions_link = "<a class='btn btn-outline-success' href='/admissions'>Admissions</a>" if role == "secretary" else ""
        documents_link = "<a class='btn btn-outline-success' href='/documents'>Documents</a>" if role == "secretary" else ""
        parent_contacts_link = "<a class='btn btn-outline-success' href='/parents'>Parents / Guardians</a>" if role == "secretary" else ""
        appointments_link = "<a class='btn btn-outline-success' href='/appointments'>Appointments</a>" if role == "secretary" else ""
        announcements_link = "<a class='btn btn-outline-success' href='/announcements'>Announcements</a>" if role == "secretary" else ""
        correspondence_link = "<a class='btn btn-outline-success' href='/correspondence'>Correspondence</a>" if role == "secretary" else ""
        letters_link = "<a class='btn btn-outline-success' href='/letters-certificates'>Letters & Certificates</a>" if role == "secretary" else ""
        lost_card_link = "<a class='btn btn-outline-danger' href='/rfid/report-lost'>Report Lost Card</a>" if role == "secretary" else ""
        reports_link = "<a class='btn btn-outline-success' href='/reports'>Reports</a>" if role == "secretary" else ""
        activity_history_link = "<a class='btn btn-outline-success' href='/activity-history'>Activity History</a>" if role == "secretary" else ""
        return page(titles[role], f"<section class='panel'><h1>{titles[role]}</h1><p>Welcome, {current_user.full_name}. Use the modules available to your role.</p><div class='d-flex gap-2 flex-wrap'><a class='btn btn-accent' href='/students'>Students</a>{admissions_link}{documents_link}{parent_contacts_link}{appointments_link}{announcements_link}{correspondence_link}{letters_link}{lost_card_link}{reports_link}{activity_history_link}<a class='btn btn-outline-success' href='/attendance'>Attendance</a><a class='btn btn-outline-success' href='/day-schedule'>Day Schedule</a><a class='btn btn-outline-success' href='/timetable'>Academic Timetable</a><a class='btn btn-outline-success' href='/messages'>Messages</a></div></section>", role)
    records=attendance_for_student(current_user.id); rows="".join(f"<tr><td>{a.day}</td><td><span class='pill'>{a.status}</span></td><td>{a.arrival_time or '-'}</td><td>{a.afternoon_time or '-'}</td></tr>" for a in records)
    return page("Student Dashboard",f"""<div class='dashboard-heading'><div><span class='pill'>STUDENT PORTAL</span><h1 class='mt-2'>My <span class='accent'>Attendance</span></h1><p>Read-only attendance records for your account.</p></div><div class='d-flex gap-2 flex-wrap'><a class='btn btn-accent' href='/student/profile'>My Student Profile</a><a class='btn btn-outline-success' href='/timetable'>My Timetable</a><a class='btn btn-outline-success' href='/day-schedule'>Day Schedule</a><a class='btn btn-outline-success' href='/grades'>My Academic Report</a></div></div><section class='panel'><div class='table-responsive'><table class='table'><thead><tr><th>Date</th><th>Status</th><th>Morning Time</th><th>Afternoon Time</th></tr></thead><tbody>{rows or '<tr><td colspan="4" class="muted">No attendance records have been saved yet.</td></tr>'}</tbody></table></div></section>""","student")


def secretary_analytics():
    if current_user.role != "secretary":
        abort(403)
    today = datetime.date.today()
    labels = []
    attendance = []
    student_activity = []
    for days_ago in range(6, -1, -1):
        date = today - datetime.timedelta(days=days_ago)
        labels.append(date.strftime("%d %b"))
        attendance.append(Attendance.query.filter_by(day=date.isoformat()).count())
        start = datetime.datetime.combine(date, datetime.time.min)
        end = start + datetime.timedelta(days=1)
        student_activity.append(ActivityLog.query.filter(
            ActivityLog.created_at >= start,
            ActivityLog.created_at < end,
            ActivityLog.action.in_({"Student registered", "Admission converted", "Student removed"}),
        ).count())
    return jsonify({"labels": labels, "attendance": attendance, "student_activity": student_activity,
                    "updated_at": datetime.datetime.now().strftime("%H:%M:%S")})

def parent_child(student_id):
    student = db.session.get(User, student_id)
    if not student or student.role != "student" or not guardian_can_access_student(current_user.id, student.id):
        abort(403)
    records = attendance_for_student(student.id)
    txs = FeeTransaction.query.filter_by(student_id=student.id).all()
    total_paid = sum(t.amount for t in txs)
    fee_requirements = FeeRequirement.query.filter_by(student_id=student.id).order_by(FeeRequirement.due_date).all()
    total_required = sum(requirement.amount for requirement in fee_requirements)
    balance_remaining = max(0.0, total_required - total_paid)
    book_loans = BookLoan.query.filter_by(student_id=student.id).order_by(BookLoan.borrowed_date.desc(), BookLoan.id.desc()).all()
    discipline_cases = DisciplineCase.query.filter_by(student_id=student.id, is_published=True).order_by(DisciplineCase.id.desc()).all()

    att_rows = "".join(f"<tr><td>{a.day}</td><td><span class='pill'>{a.status}</span></td><td>{a.arrival_time or '-'}</td><td>{a.afternoon_time or '-'}</td><td>{a.source or 'Manual'}</td></tr>" for a in records)
    attendance_counts = {status: sum(1 for record in records if record.status == status) for status in ("Present", "Absent", "Late")}
    attendance_summary = "".join(f"<div class='stat'><div class='stat-value'>{attendance_counts[status]}</div><div class='stat-label'>{status} days</div></div>" for status in ("Present", "Absent", "Late"))
    tx_rows = "".join(f"<tr><td>{t.created_at}</td><td>{t.amount:,.2f} RWF</td><td>{t.method}</td><td>{t.reference or '-'}</td></tr>" for t in txs)
    fee_rows = "".join(f"<tr><td>{requirement.title}</td><td>{requirement.amount:,.2f} RWF</td><td>{requirement.due_date.isoformat()}</td><td>{requirement.details or '-'}</td></tr>" for requirement in fee_requirements)
    book_loan_rows = "".join(f"<tr><td>{loan.book.title if loan.book else '-'}</td><td>{loan.borrowed_date.isoformat()}</td><td>{loan.due_date.isoformat()}</td><td>{loan.returned_date.isoformat() if loan.returned_date else '-'}</td><td>{'Returned' if loan.returned_date else 'Overdue' if loan.due_date < datetime.date.today() else 'Borrowed'}</td></tr>" for loan in book_loans)
    discipline_rows = "".join(f"<tr><td>{escape(case.created_at)}</td><td>{escape(case.record_type or 'Concern')}</td><td>{escape(case.details)}</td><td>{escape(case.action_taken or '-')}</td><td>{escape(case.remarks or '-')}</td></tr>" for case in discipline_cases)
    timetable_entries = TimetableEntry.query.filter_by(class_name=student.class_name).order_by(TimetableEntry.day_of_week, TimetableEntry.time_slot).all() if student.class_name else []
    timetable_rows = "".join(f"<tr><td>{entry.day_of_week}</td><td>{entry.time_slot or '-'}</td><td>{entry.subject}</td><td>{entry.teacher_name or '-'}</td></tr>" for entry in timetable_entries)
    day_schedule_query = DayScheduleEntry.query.filter(DayScheduleEntry.is_published.is_(True), DayScheduleEntry.schedule_date >= datetime.date.today())
    day_schedule_query = day_schedule_query.filter(db.or_(DayScheduleEntry.class_name.is_(None), DayScheduleEntry.class_name == student.class_name))
    day_schedule_entries = day_schedule_query.order_by(DayScheduleEntry.schedule_date, DayScheduleEntry.start_time).all()
    day_schedule_rows = "".join(f"<tr><td>{entry.schedule_date.isoformat()}</td><td>{entry.start_time or '-'}{f' - {entry.end_time}' if entry.end_time else ''}</td><td>{entry.activity}</td><td>{entry.details or '-'}</td></tr>" for entry in day_schedule_entries)

    body = f"""<section class="panel"><h1>Child Overview: <span class="accent">{student.full_name}</span></h1><p class="muted">Class: {student.class_name or '-'} | Level: {student.level or '-'} | Trade: {student.trade or '-'}</p><div class="grid my-4"><div class="stat"><strong>{total_required:,.2f} RWF</strong><div>Total Fees Required</div></div><div class="stat"><strong>{total_paid:,.2f} RWF</strong><div>Total Fees Paid</div></div><div class="stat"><strong>{balance_remaining:,.2f} RWF</strong><div>Outstanding Balance</div></div></div><h3 class="mt-4">Fee Requirements & Deadlines</h3><div class="table-responsive"><table class="table"><tr><th>Requirement</th><th>Amount</th><th>Deadline</th><th>Details</th></tr>{fee_rows or '<tr><td colspan="4" class="muted">No fee requirements have been entered.</td></tr>'}</table></div><h3 class="mt-4">Library Loans</h3><div class="table-responsive"><table class="table"><tr><th>Book</th><th>Borrowed</th><th>Due Date</th><th>Returned</th><th>Status</th></tr>{book_loan_rows or '<tr><td colspan="5" class="muted">No book loans are recorded.</td></tr>'}</table></div><h3 class="mt-4">Published Behavior Reports</h3><div class="table-responsive"><table class="table"><tr><th>Date</th><th>Type</th><th>Details</th><th>Action Taken</th><th>Remarks</th></tr>{discipline_rows or '<tr><td colspan="5" class="muted">No published behavior reports are available.</td></tr>'}</table></div><h3 class="mt-4">Academic Timetable</h3><p class="muted">The class schedule for this child.</p><div class="table-responsive"><table class="table"><tr><th>Day</th><th>Time Slot</th><th>Subject</th><th>Teacher</th></tr>{timetable_rows or '<tr><td colspan="4" class="muted">No timetable has been published for this class yet.</td></tr>'}</table></div><h3 class="mt-4">Published Day Schedule</h3><p class="muted">Daily program and activities for this child.</p><div class="table-responsive"><table class="table"><tr><th>Date</th><th>Time</th><th>Activity</th><th>Details</th></tr>{day_schedule_rows or '<tr><td colspan="4" class="muted">No published activities are available.</td></tr>'}</table></div><h3 class="mt-4">Attendance Summary</h3><div class="grid mb-4">{attendance_summary}</div><h3 class="mt-4">Attendance History & RFID / Scan Times</h3><p class="muted">Daily status, school arrival time, and afternoon attendance for this student.</p><div class="table-responsive"><table class="table"><tr><th>Date</th><th>Attendance</th><th>Arrival Time</th><th>Afternoon Attendance</th><th>Source</th></tr>{att_rows or '<tr><td colspan="5" class="muted">No attendance history is available for this student.</td></tr>'}</table></div><h3 class="mt-4">Payment History</h3><table class="table"><tr><th>Date</th><th>Amount</th><th>Method</th><th>Reference</th></tr>{tx_rows or '<tr><td colspan="4" class="muted">No payments have been recorded.</td></tr>'}</table><a class="btn btn-outline-success mt-3" href="/dashboard" style="border-color:var(--accent);color:var(--text)">Back to Dashboard</a></section>"""
    published_grades = Grade.query.filter_by(student_id=student.id, is_published=True).order_by(Grade.academic_year.desc(), Grade.term, Grade.subject).all()
    grade_rows = "".join(f"<tr><td>{escape(grade.academic_year or '-')}</td><td>{escape(grade.term or '-')}</td><td>{escape(grade.subject)}</td><td>{grade.marks:g} / {grade.max_marks:g}</td><td>{escape(grade.remarks or '-')}</td></tr>" for grade in published_grades)
    assessment_submissions = AssessmentSubmission.query.filter_by(student_id=student.id).order_by(AssessmentSubmission.submitted_at.desc()).all()
    assessment_submissions = [submission for submission in assessment_submissions if submission.assessment.is_published]
    assessment_rows = "".join(f"<tr><td>{escape(submission.assessment.title)}</td><td>{escape(submission.assessment.subject)}</td><td>{escape(submission.submitted_at)}</td><td>{f'{submission.score:g} / {submission.assessment.max_score:g}' if submission.is_graded and submission.score is not None else 'Awaiting teacher score'}</td><td>{escape(submission.feedback or '-')}</td></tr>" for submission in assessment_submissions)
    no_grade_rows = '<tr><td colspan="5" class="muted">No published academic results are available.</td></tr>'
    no_assessment_rows = '<tr><td colspan="5" class="muted">No assessment submissions are available.</td></tr>'
    academic_html = f"<h3 class='mt-4'>Published Academic Results</h3><div class='table-responsive'><table class='table'><tr><th>Year</th><th>Term</th><th>Lesson</th><th>Marks</th><th>Teacher Remarks</th></tr>{grade_rows or no_grade_rows}</table></div>"
    assessment_html = f"<h3 class='mt-4'>e-Learning Assessment Results</h3><div class='table-responsive'><table class='table'><tr><th>Assessment</th><th>Subject</th><th>Submitted</th><th>Score</th><th>Feedback</th></tr>{assessment_rows or no_assessment_rows}</table></div><a class='btn btn-outline-success mb-3' href='/assessments'>Open Assessments</a>"
    body = body.replace('<h3 class="mt-4">Academic Timetable</h3>', academic_html + assessment_html + '<h3 class="mt-4">Academic Timetable</h3>')
    return page("Child Details", body, "parent")

def register_routes(app):
    app.add_url_rule('/dashboard', endpoint='dashboard', view_func=permission_for('dashboard')(dashboard), methods=['GET'])
    app.add_url_rule('/dashboard/secretary-analytics', endpoint='secretary_analytics', view_func=permission_for('dashboard')(secretary_analytics), methods=['GET'])
    app.add_url_rule('/parent/child/<int:student_id>', endpoint='parent_child', view_func=permission_for('parent_child')(parent_child), methods=['GET'])
