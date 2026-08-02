"""Periodically triggers the reminder and missed-appointment check actors.

Neither `check_due_reminders` nor `check_missed_appointments` has anything
to react to — there's no event that means "an appointment's reminder is
due" or "an appointment just became overdue"; they're just true on a
schedule. A plain interval loop is simpler than routing that through the
transactional outbox (which exists for react-to-a-domain-event dispatch,
not time-based dispatch) or adding a cron dependency — matches the "simple
first version" scheduling approach already noted in
`workflows/appointment_reminders.py`'s docstring.

Runs as a second concurrent loop in the `worker` service's process — see
`main.py` — alongside the outbox consumer. Both are cheap, low-frequency
polling loops for a single small clinic; splitting this into its own
service would be more deployment surface for no real benefit at this
scale.
"""

import asyncio

import structlog

from medical_worker.workflows.appointment_reminders import check_due_reminders
from medical_worker.workflows.missed_appointment import check_missed_appointments

logger = structlog.get_logger(__name__)

# Reminder windows already tolerate ±5 minutes (see REMINDER_WINDOWS in
# appointment_reminders.py) — checking every 5 minutes means consecutive
# checks' windows overlap with no gap, so every appointment gets caught by
# at least one check regardless of exactly when it lands relative to a
# check's own timing.
REMINDER_CHECK_INTERVAL_SECONDS = 300
MISSED_APPOINTMENT_CHECK_INTERVAL_SECONDS = 300


async def run_scheduler() -> None:
    logger.info(
        "scheduler.started",
        reminder_interval=REMINDER_CHECK_INTERVAL_SECONDS,
        missed_appointment_interval=MISSED_APPOINTMENT_CHECK_INTERVAL_SECONDS,
    )
    await asyncio.gather(_run_reminder_loop(), _run_missed_appointment_loop())


async def _run_reminder_loop() -> None:
    while True:
        try:
            check_due_reminders.send()
        except Exception:
            # A Redis hiccup enqueuing this tick shouldn't kill the whole
            # scheduler loop — just log and try again next tick.
            logger.exception("scheduler.check_due_reminders_failed")
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)


async def _run_missed_appointment_loop() -> None:
    while True:
        try:
            check_missed_appointments.send()
        except Exception:
            logger.exception("scheduler.check_missed_appointments_failed")
        await asyncio.sleep(MISSED_APPOINTMENT_CHECK_INTERVAL_SECONDS)
