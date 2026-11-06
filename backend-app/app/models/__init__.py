from .user import User
from .attendance import Attendance, AttendanceAuditTrail
from .rfid import PendingCard, RFIDCard, RFIDDevice, RFIDScanLog
from .fees import FeeTransaction, FeeRequirement
from .library import Book, BookLoan
from .discipline import DisciplineCase
from .behavior import BehaviorRecord
from .messaging import (SchoolMessage, UserNotification, MessageConversation,
                        MessageParticipant, MessageReport, MessagePermission,
                        MessageAuditEvent, OfficialNoticePermission,
                        OfficialNotice, OfficialNoticeAuditEvent)
from .assessment import Assessment, AssessmentQuestion, AssessmentSubmission, AssessmentAttempt
from .rubric import GradingRubric, GradingRubricCriterion
from .parent_notifications import ParentNotificationPreference
from .learning_material import LearningMaterial
from .academics import Grade, TimetableEntry, DayScheduleEntry, AcademicSubject, SyllabusCoverage, LessonPlan, ReportCardApproval
from .setting import Setting
from .admission import AdmissionApplicant
from .student_document import StudentDocument
from .appointment import Appointment
from .meetings import (StudentGuardian, Meeting, MeetingParticipant, MeetingAttendance,
                       MeetingAgendaItem, MeetingMinutes, MeetingMinutesRevision,
                       MeetingActionItem, MeetingActionComment, MeetingAuditEvent,
                       MeetingNotificationLog, RoomReservation)
from .announcement import Announcement
from .correspondence import Correspondence
from .activity import ActivityLog
from .academic_structure import School, Department, Trade, SchoolClass, AcademicModule, AcademicYear, AcademicTerm
from .enrollment import AcademicEnrollment
from .welfare import StudentWelfareRecord, DailyWelfareReport, WelfareAuditEvent

__all__ = [
    "School", "Department", "Trade", "SchoolClass", "AcademicModule", "AcademicYear", "AcademicTerm",
    "AcademicEnrollment", "User", "Attendance", "AttendanceAuditTrail", "PendingCard",
    "RFIDCard", "RFIDDevice", "RFIDScanLog", "FeeTransaction", "FeeRequirement",
    "Book", "BookLoan", "DisciplineCase", "BehaviorRecord", "SchoolMessage",
    "UserNotification", "MessageConversation", "MessageParticipant", "MessageReport",
    "MessagePermission", "MessageAuditEvent", "OfficialNoticePermission",
    "OfficialNotice", "OfficialNoticeAuditEvent", "Assessment", "AssessmentQuestion",
    "AssessmentSubmission", "AssessmentAttempt", "GradingRubric",
    "GradingRubricCriterion", "ParentNotificationPreference", "LearningMaterial",
    "Grade", "TimetableEntry", "DayScheduleEntry", "AcademicSubject",
    "SyllabusCoverage", "LessonPlan", "ReportCardApproval", "Setting",
    "AdmissionApplicant", "StudentDocument", "Appointment", "StudentGuardian",
    "Meeting", "MeetingParticipant", "MeetingAttendance", "MeetingAgendaItem",
    "MeetingMinutes", "MeetingMinutesRevision", "MeetingActionItem",
    "MeetingActionComment", "MeetingAuditEvent", "MeetingNotificationLog",
    "RoomReservation", "Announcement", "Correspondence", "ActivityLog",
    "StudentWelfareRecord", "DailyWelfareReport", "WelfareAuditEvent",
]
