from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.auth import hash_password
from app.config import settings
from app.db import engine
from app.enums import CraActivity, CraCategory, ExpenseType, Status, UserRole
from app.models import CraEvent, CraMonth, NoteFrais, User


def seed_demo_data() -> None:
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == settings.demo_user_email)).first()
        if existing:
            return

        user = User(
            email=settings.demo_user_email,
            password_hash=hash_password(settings.demo_user_password),
            full_name=settings.demo_user_fullname,
            role=UserRole.MEMBER,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        assert user.id is not None

        today = date.today()
        current_month = today.strftime('%Y-%m')

        # A couple of CRA events for the current month
        for offset in range(0, 3):
            day = today - timedelta(days=offset)
            session.add(
                CraEvent(
                    user_id=user.id,
                    month=day.strftime('%Y-%m'),
                    categorie=CraCategory.TRAVAIL,
                    activity=CraActivity.PRESTATION,
                    start_date=day,
                    end_date=day,
                    all_day=True,
                    nb=1.0,
                    description='Prestation client',
                )
            )

        # A few past validated months
        for i in range(1, 5):
            year = today.year if today.month - i > 0 else today.year - 1
            month_num = (today.month - i - 1) % 12 + 1
            month_str = f'{year:04d}-{month_num:02d}'
            session.add(
                CraMonth(
                    user_id=user.id,
                    month=month_str,
                    status=Status.VALIDATED,
                    description_tasks='Activités du mois',
                    submitted_at=datetime.utcnow(),
                    validated_at=datetime.utcnow(),
                )
            )

        # A couple of expenses
        session.add(
            NoteFrais(
                user_id=user.id,
                month=current_month,
                type=ExpenseType.RESTAURANT,
                description='Repas client',
                total_amount=42.5,
                billable_to_client=True,
                status=Status.PENDING,
            )
        )
        session.add(
            NoteFrais(
                user_id=user.id,
                month=current_month,
                type=ExpenseType.TELEPHONIE,
                description='Forfait mobile',
                total_amount=29.99,
                billable_to_client=False,
                status=Status.VALIDATED,
            )
        )

        session.commit()
