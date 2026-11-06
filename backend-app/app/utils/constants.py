ROLE_ALIASES = {
    "admin": "master_admin",
    "administrator": "master_admin",
    "super_admin": "master_admin",
    "master_admin": "master_admin",
    "teacher": "teacher",
    "accountant": "accountant",
    "librarian": "librarian",
    "discipline": "discipline",
    "disciplinary": "discipline",
    "patron": "patron",
    "matron": "matron",
    "auditor": "auditor",
    "secretary": "secretary",
    "parent": "parent",
    "student": "student",
}

ROLES = (
    "admin",
    "master_admin",
    "head_teacher",
    "teacher",
    "accountant",
    "librarian",
    "discipline",
    "patron",
    "matron",
    "auditor",
    "secretary",
    "parent",
    "student",
)
ADMIN_ROLES = {"master_admin"}
STAFF_ROLES = set(ROLES) - {"student", "parent"}


def normalize_role(role):
    if role is None:
        return None
    key = str(role).strip().lower()
    return ROLE_ALIASES.get(key, key)


ROLE_ACCESS = {
    "dashboard": {"master_admin", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student", "auditor"},
    "students": {"master_admin", "teacher", "librarian", "accountant", "discipline", "patron", "matron", "secretary"},
    "admissions": {"master_admin", "head_teacher", "secretary"},
    "documents": {"master_admin", "head_teacher", "secretary"},
    "parent_contacts": {"master_admin", "head_teacher", "secretary"},
    "appointments": {"master_admin", "head_teacher", "secretary", "teacher", "discipline", "patron", "matron", "parent"},
    "meetings": {"master_admin", "head_teacher", "secretary", "teacher", "discipline", "patron", "matron", "parent"},
    "meeting_api": {"master_admin", "head_teacher", "secretary", "teacher", "discipline", "patron", "matron", "parent"},
    "meeting_admin": {"master_admin", "head_teacher", "secretary"},
    "meeting_settings": {"master_admin", "head_teacher"},
    "meeting_audit": {"master_admin"},
    "announcements": {"master_admin", "head_teacher", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student"},
    "correspondence": {"master_admin", "head_teacher", "secretary"},
    "letters_certificates": {"master_admin", "head_teacher", "secretary"},
    "reports": {"master_admin", "head_teacher", "secretary"},
    "activity_history": {"master_admin", "head_teacher", "secretary"},
    "card_lookup": {"master_admin", "teacher", "secretary"},
    "report_lost_card": {"master_admin", "head_teacher", "secretary"},
    "attendance": {"master_admin", "teacher", "discipline", "patron", "matron", "secretary", "librarian", "parent", "student"},
    "attendance_times": {"master_admin"},
    "export_attendance": {"master_admin", "teacher", "secretary"},
    "grades": {"master_admin", "teacher", "secretary", "parent", "student"},
    "report_card": {"master_admin", "teacher", "secretary", "parent", "student"},
    "export_report_card": {"master_admin", "teacher", "secretary", "parent", "student"},
    "timetable": {"master_admin", "teacher", "librarian", "accountant", "discipline", "patron", "matron", "secretary", "parent", "student"},
    "academic_management": {"master_admin", "head_teacher", "teacher"},
    "school_structure": {"master_admin", "head_teacher", "teacher"},
    "day_schedule": {"master_admin", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student", "auditor"},
    "fees": {"master_admin", "accountant", "parent", "student", "secretary"},
    "library": {"master_admin", "librarian", "teacher", "student", "parent"},
    "discipline": {"master_admin", "teacher", "discipline", "patron", "matron", "secretary", "parent", "student"},
    "behavior": {"master_admin", "head_teacher", "teacher", "discipline", "patron", "matron", "parent", "student"},
    "welfare": {"master_admin", "head_teacher", "patron", "matron"},
    "messages": {"master_admin", "head_teacher", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student", "auditor"},
    "notifications": {"master_admin", "head_teacher", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student", "auditor"},
    "assessments": {"master_admin", "teacher", "student", "parent"},
    "create_rubric": {"master_admin", "teacher"},
    "learning_materials": {"master_admin", "head_teacher", "secretary", "teacher", "student", "parent"},
    "learning_material_file": {"master_admin", "head_teacher", "secretary", "teacher", "student", "parent"},
    "submit_assessment": {"student"},
    "start_assessment": {"student"},
    "grade_assessment": {"master_admin", "teacher"},
    "assessment_file": {"master_admin", "teacher", "student", "parent"},
    "assessment_submission_file": {"master_admin", "teacher", "student", "parent"},
    "classes_modules": {"master_admin", "head_teacher", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student", "auditor"},
    "classes_modules_edit": {"master_admin", "head_teacher", "secretary"},
    "welfare": {"master_admin", "head_teacher", "patron", "matron"},
    "welfare_search": {"master_admin", "head_teacher", "patron", "matron"},
    "welfare_create": {"patron", "matron"},
    "welfare_student": {"master_admin", "head_teacher", "patron", "matron"},
    "welfare_group": {"master_admin", "head_teacher", "patron", "matron"},
    "welfare_daily_submit": {"patron", "matron"},
    "welfare_admin": {"master_admin", "head_teacher"},
    "welfare_reports": {"master_admin", "head_teacher"},
    "welfare_report_download": {"master_admin", "head_teacher"},
    "welfare_ai": {"master_admin", "head_teacher", "patron", "matron"},
    "welfare_settings": {"master_admin", "head_teacher"},
    "welfare_audit": {"master_admin", "head_teacher"},
    "api_welfare_students": {"master_admin", "head_teacher", "patron", "matron"},
    "api_welfare_student_summary": {"master_admin", "head_teacher", "patron", "matron"},
    "api_welfare_repeated_concerns": {"master_admin", "head_teacher", "patron", "matron"},
    "api_welfare_ai_answer": {"master_admin", "head_teacher", "patron", "matron"},
    "admin": {"master_admin"},
    "parent_child": {"parent"},
    "parent_notification_settings": {"parent"},
    "student_profile": {"master_admin", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student"},
    "student_photo": {"master_admin", "teacher", "accountant", "librarian", "discipline", "patron", "matron", "secretary", "parent", "student"},
}

# Head Teachers supervise academic and student affairs across the school.
for _endpoint in (
    "dashboard", "students", "card_lookup", "report_lost_card", "admissions", "documents", "parent_contacts", "appointments", "meetings", "meeting_api", "meeting_admin", "meeting_settings", "announcements", "correspondence", "letters_certificates", "reports", "activity_history", "attendance", "attendance_times",
    "export_attendance", "grades", "report_card", "export_report_card", "timetable",
    "day_schedule", "discipline", "behavior", "welfare", "assessments", "create_rubric", "grade_assessment",
    "learning_materials", "learning_material_file", "assessment_file",
    "assessment_submission_file", "student_profile", "student_photo",
):
    ROLE_ACCESS[_endpoint].add("head_teacher")
VALID_ATTENDANCE = {"Present", "Absent", "Late", "Permission"}
DEFAULT_MORNING_START = "06:30"
DEFAULT_LATE_AFTER = "08:00"
DEFAULT_AFTERNOON_START = "16:00"
DEFAULT_AFTERNOON_END = "16:30"
SCHOOL_STRUCTURE = {
    "ICT and Multimedia": {
        "Software Development": {
            "L3": ["L3 Software Development"],
            "L4": ["L4 Software Development A", "L4 Software Development B"],
            "L5": ["L5 Software Development"],
        },
        "Networking and Internet Technology": {
            "L3": ["L3 Networking and Internet Technology"],
            "L4": ["L4 Networking and Internet Technology A", "L4 Networking and Internet Technology B"],
            "L5": ["L5 Networking and Internet Technology"],
        },
        "Computer System and Architecture": {
            "L3": ["L3 Computer System and Architecture"],
            "L4": ["L4 Computer System and Architecture"],
            "L5": ["L5 Computer System and Architecture"],
        },
    },
    "Fashion and Design": {
        "Fashion and Design": {
            "L3": ["L3 Fashion and Design"],
            "L4": ["L4 Fashion and Design"],
            "L5": ["L5 Fashion and Design"],
        },
    },
    "Professional Accountant": {
        "Professional Accountant": {
            "S4": ["S4 Accountant A", "S4 Accountant B"],
            "S5": ["S5 Accountant"],
            "S6": ["S6 Accountant"],
        },
    },
}
DEPARTMENTS = list(SCHOOL_STRUCTURE)
TRADE_DEPARTMENT = {
    trade: department
    for department, trade_map in SCHOOL_STRUCTURE.items()
    for trade in trade_map
}
TRADES = list(TRADE_DEPARTMENT)
PROGRAM_LEVELS = {
    trade: list(levels)
    for trade_map in SCHOOL_STRUCTURE.values()
    for trade, levels in trade_map.items()
}
CLASS_GROUPS = {
    trade: {level: list(class_names) for level, class_names in levels.items()}
    for trade_map in SCHOOL_STRUCTURE.values()
    for trade, levels in trade_map.items()
}
CLASS_TRADE_LEVEL = {
    class_name: (trade, level)
    for trade_map in SCHOOL_STRUCTURE.values()
    for trade, levels in trade_map.items()
    for level, class_names in levels.items()
    for class_name in class_names
}
CLASS_DEPARTMENT = {
    class_name: department
    for department, trade_map in SCHOOL_STRUCTURE.items()
    for levels in trade_map.values()
    for class_names in levels.values()
    for class_name in class_names
}
CLASS_NAMES = list(CLASS_TRADE_LEVEL)
LEGACY_CLASS_ALIASES = {
    "L3 Fashion Design": "L3 Fashion and Design",
    "L4 Fashion Design": "L4 Fashion and Design",
    "L5 Fashion Design": "L5 Fashion and Design",
    "S4 Professional Accountant A": "S4 Accountant A",
    "S6 Professional Accountant": "S6 Accountant",
}
ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
