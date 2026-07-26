"""Marks appointments as no-show once they're past end time plus a grace
period without a check-in. Triggered periodically, same as
`appointment_reminders.check_due_reminders`.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import dramatiq
import structlog
from sqlalchemy import select

from medical_api.core.database import async_session_factory
from medical_api.modules.scheduling.models import (
    Appointment,
    AppointmentStatus,
    AppointmentStatusHistory,
)
from medical_worker import broker  # noqa: F401  (registers the Redis broker)

logger = structlog.get_logger(__name__)

GRACE_PERIOD = timedelta(minutes=30)


@dramatiq.actor(max_retries=3)
def check_missed_appointments() -> None:
    asyncio.run(_check())


async def _check() -> None:
    cutoff = datetime.now(UTC) - GRACE_PERIOD
    async with async_session_factory() as session:
        stmt = select(Appointment).where(
            Appointment.status.in_((AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)),
            Appointment.ends_at < cutoff,
        )
        overdue = list((await session.execute(stmt)).scalars().all())
        for appointment in overdue:
            previous_status = appointment.status
            appointment.status = AppointmentStatus.NO_SHOW
            session.add(
                AppointmentStatusHistory(
                    appointment_id=appointment.id,
                    from_status=previous_status,
                    to_status=AppointmentStatus.NO_SHOW,
                    reason="No check-in recorded within grace period",
                )
            )
        if overdue:
            await session.commit()
            logger.info("appointments.marked_no_show", count=len(overdue))
