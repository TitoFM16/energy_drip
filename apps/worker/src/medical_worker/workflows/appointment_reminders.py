"""24h/2h appointment reminders.

Intended to be triggered periodically (every few minutes) by an external
scheduler — e.g. a cron entry or `dramatiq-crontab` calling
`check_due_reminders.send()`. Kept as a plain dramatiq actor rather than a
long-running Temporal workflow for this first version, per the "simple
first version: Redis + a task queue" guidance in docs/architecture; migrate
to Temporal if reminders need to react to mid-flight signals
(reschedule/cancel) rather than just re-checking status on each tick.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import dramatiq
import structlog
from sqlalchemy import select

from medical_api.modules.notifications.models import NotificationChannel, NotificationMessage
from medical_api.modules.patients.repository import PatientRepository
from medical_api.modules.scheduling.models import Appointment, AppointmentStatus
from medical_worker import broker  # noqa: F401  (registers the Redis broker)
from medical_worker.activities.send_whatsapp import send_whatsapp_message
from medical_worker.database import async_session_factory

logger = structlog.get_logger(__name__)

REMINDER_WINDOWS = {"24h": timedelta(hours=24), "2h": timedelta(hours=2)}
_ACTIVE_STATUSES = (
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.CONSENT_PENDING,
    AppointmentStatus.CONSENT_COMPLETED,
)


@dramatiq.actor(max_retries=3)
def check_due_reminders() -> None:
    asyncio.run(_check_all_windows())


async def _check_all_windows() -> None:
    for label, lead_time in REMINDER_WINDOWS.items():
        await _check_window(label, lead_time)


async def _check_window(label: str, lead_time: timedelta) -> None:
    template_key = f"appointment_reminder_{label}"
    now = datetime.now(UTC)
    window_start, window_end = (
        now + lead_time - timedelta(minutes=5),
        now + lead_time + timedelta(minutes=5),
    )

    async with async_session_factory() as session:
        stmt = select(Appointment).where(
            Appointment.status.in_(_ACTIVE_STATUSES),
            Appointment.starts_at >= window_start,
            Appointment.starts_at < window_end,
        )
        due_appointments = list((await session.execute(stmt)).scalars().all())
        if not due_appointments:
            return

        already_sent_stmt = select(NotificationMessage.payload).where(
            NotificationMessage.template_key == template_key
        )
        already_sent_ids = {
            row["appointment_id"] for row in (await session.execute(already_sent_stmt)).scalars()
        }

        patient_repo = PatientRepository(session)
        for appointment in due_appointments:
            if str(appointment.id) in already_sent_ids:
                continue
            patient = await patient_repo.get(appointment.organization_id, appointment.patient_id)
            if patient is None or not patient.phone_number:
                continue
            message = NotificationMessage(
                organization_id=appointment.organization_id,
                channel=NotificationChannel.WHATSAPP,
                recipient=patient.phone_number,
                template_key=template_key,
                payload={"appointment_id": str(appointment.id)},
            )
            session.add(message)
            # Flush (not commit) so message.id is populated before we hand
            # it to the send actor — the batch still commits once, below.
            await session.flush()
            send_whatsapp_message.send(
                patient.phone_number,
                template_key,
                [patient.first_name, appointment.starts_at.isoformat()],
                str(message.id),
            )
        await session.commit()
