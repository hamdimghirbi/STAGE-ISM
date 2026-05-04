from enum import Enum


class CraCategory(str, Enum):
    ABSENCE = 'Absence'
    TRAVAIL = 'Travail'


class CraActivity(str, Enum):
    # Travail activities
    PRESTATION = 'Prestation'
    HNO = 'HNO'
    ASTREINTE = 'Astreinte'
    # Absence activities
    CP = 'CP'
    RTT = 'RTT'
    MALADIE = 'Maladie'
    SANS_SOLDE = 'Sans solde'
    AUTRE = 'Autre'


# Mapping of which activities belong to which category
ACTIVITY_BY_CATEGORY: dict[CraCategory, list[CraActivity]] = {
    CraCategory.TRAVAIL: [
        CraActivity.PRESTATION,
        CraActivity.HNO,
        CraActivity.ASTREINTE,
    ],
    CraCategory.ABSENCE: [
        CraActivity.CP,
        CraActivity.RTT,
        CraActivity.MALADIE,
        CraActivity.SANS_SOLDE,
        CraActivity.AUTRE,
    ],
}


class ExpenseType(str, Enum):
    INDEMNITES_KM = 'Indemnités kilométriques'
    AUTRE = 'Autre'
    RESTAURANT = 'Restaurant'
    MATERIEL = 'Materiel'
    TITRE_TRANSPORT = 'Titre de transport'
    TELEPHONIE = 'Telephonie'
    TELETRAVAIL = 'Teletravail'


class Status(str, Enum):
    DRAFT = 'Draft'
    PENDING = 'Pending'
    VERIFIED = 'Verified'
    VALIDATED = 'Validated'
    REJECTED = 'Rejected'


class UserRole(str, Enum):
    MEMBER = 'member'
    ADMIN = 'admin'
    RH = 'rh'
