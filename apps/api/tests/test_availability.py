import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock

import pytest

from medical_api.core.exceptions import ConflictError
from medical_api.modules.scheduling.models import Appointment, AvailabilityRule
from medical_api.modules.scheduling.service import AvailabilityService

ORG_ID = uuid.uuid4()
PRACTITIONER_ID = uuid.uuid4()


def _rule(weekday: int, start: time, end: time) -> AvailabilityRule:
    return AvailabilityRule(
        organization_id=ORG_ID,
        practitioner_id=PRACTITIONER_ID,
        weekday=weekday,
        start_time=start,
        end_time=end,
    )


def _appointment(starts_at: datetime, ends_at: datetime) -> Appointment:
    return Appointment(
        organization_id=ORG_ID,
        patient_id=uuid.uuid4(),
        practitioner_id=PRACTITIONER_ID,
        starts_at=starts_at,
        ends_at=ends_at,
    )


def _service(rules: list[AvailabilityRule], busy: list[Appointment]) -> AvailabilityService:
    repository = AsyncMock()
    repository.list_rules.return_value = rules
    appointments = AsyncMock()
    appointments.list_for_practitioner_range.return_value = busy
    return AvailabilityService(repository, appointments)


# A future Monday, so slots aren't filtered out by the "no past slots" rule.
_NEXT_MONDAY = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)


async def test_computes_slots_from_rule_with_no_conflicts():
    service = _service([_rule(_NEXT_MONDAY.weekday(), time(9, 0), time(10, 0))], [])
    slots = await service.compute_slots(ORG_ID, PRACTITIONER_ID, _NEXT_MONDAY, _NEXT_MONDAY, 30)
    assert len(slots) == 2
    assert slots[0].starts_at.time() == time(9, 0)
    assert slots[1].starts_at.time() == time(9, 30)


async def test_excludes_slots_overlapping_existing_appointment():
    rule = _rule(_NEXT_MONDAY.weekday(), time(9, 0), time(10, 0))
    busy_start = datetime.combine(_NEXT_MONDAY, time(9, 0), tzinfo=UTC)
    busy_appointment = _appointment(busy_start, busy_start + timedelta(minutes=30))

    service = _service([rule], [busy_appointment])
    slots = await service.compute_slots(ORG_ID, PRACTITIONER_ID, _NEXT_MONDAY, _NEXT_MONDAY, 30)

    assert len(slots) == 1
    assert slots[0].starts_at.time() == time(9, 30)


async def test_no_rules_means_no_slots():
    service = _service([], [])
    slots = await service.compute_slots(ORG_ID, PRACTITIONER_ID, _NEXT_MONDAY, _NEXT_MONDAY, 30)
    assert slots == []


async def test_rejects_date_range_larger_than_max_window():
    service = _service([_rule(0, time(9, 0), time(10, 0))], [])
    with pytest.raises(ConflictError):
        await service.compute_slots(
            ORG_ID, PRACTITIONER_ID, _NEXT_MONDAY, _NEXT_MONDAY + timedelta(days=60), 30
        )


async def test_rejects_inverted_date_range():
    service = _service([_rule(0, time(9, 0), time(10, 0))], [])
    with pytest.raises(ConflictError):
        await service.compute_slots(
            ORG_ID, PRACTITIONER_ID, _NEXT_MONDAY, _NEXT_MONDAY - timedelta(days=1), 30
        )
