"""Import every table module so Base.metadata knows them."""

from app.models.access import AppUser, Role, RolePermission, UserSession
from app.models.audit import AuditEvent
from app.models.family import Family, FamilyAdditionalInfo, FamilyMember, FamilySibling
from app.models.goals import (
    BrgGoal,
    BrgGoalSagLink,
    BrgHypothesizedFunction,
    BrgTarget,
    BrgTargetStage,
    GoalName,
    PcgGoal,
    PcgTarget,
    PcgTargetStage,
    SagGoal,
    SagTarget,
    SagTargetStage,
)
from app.models.information import ClientAssignment, ClientGuardian, ClientInsurance, Provider
from app.models.medical import MedicalDiagnosis, MedicalInfo, MedicalSelection
from app.models.referral import Referral
from app.models.medication import Medication
from app.models.therapy import Therapy, TherapyRow
from app.models.assessment import Assessment, AssessmentBehavior, AssessmentMethod, AssessmentReadiness, AssessmentVisual
from app.models.child import Child, ChildBackground, ChildSchedule
from app.models.crisis import Crisis, CrisisPlan
from app.models.discharge import Discharge, DischargeReason
from app.models.education import Education
from app.models.treatment import Treatment
from app.models.plan import Client, TreatmentPlan

__all__ = [
    "AuditEvent",
    "AppUser",
    "Role",
    "RolePermission",
    "BrgGoal",
    "BrgGoalSagLink",
    "BrgHypothesizedFunction",
    "BrgTarget",
    "BrgTargetStage",
    "GoalName",
    "PcgGoal",
    "PcgTarget",
    "PcgTargetStage",
    "SagGoal",
    "SagTarget",
    "SagTargetStage",
    "Assessment",
    "AssessmentBehavior",
    "AssessmentMethod",
    "AssessmentReadiness",
    "AssessmentVisual",
    "Child",
    "ChildBackground",
    "ChildSchedule",
    "Client",
    "Crisis",
    "CrisisPlan",
    "MedicalDiagnosis",
    "MedicalInfo",
    "MedicalSelection",
    "Medication",
    "ClientAssignment",
    "ClientGuardian",
    "ClientInsurance",
    "Discharge",
    "DischargeReason",
    "Education",
    "Family",
    "FamilyAdditionalInfo",
    "FamilyMember",
    "FamilySibling",
    "Provider",
    "Referral",
    "Therapy",
    "TherapyRow",
    "Treatment",
    "TreatmentPlan",
    "UserSession",
]
