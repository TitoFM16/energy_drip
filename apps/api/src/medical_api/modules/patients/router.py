import uuid

from fastapi import APIRouter, Depends

from medical_api.api.dependencies import AuthenticatedUser, DbSession
from medical_api.core.security import require_roles
from medical_api.modules.audit.service import AuditService
from medical_api.modules.patients.repository import (
    EmergencyContactRepository,
    PatientContactRepository,
    PatientRepository,
)
from medical_api.modules.patients.schemas import (
    EmergencyContactCreate,
    EmergencyContactRead,
    EmergencyContactUpdate,
    PatientCommunicationPreferencesRead,
    PatientCommunicationPreferencesUpdate,
    PatientContactCreate,
    PatientContactRead,
    PatientContactUpdate,
    PatientCreate,
    PatientRead,
    PatientUpdate,
)
from medical_api.modules.patients.service import (
    EmergencyContactService,
    PatientContactService,
    PatientService,
)

router = APIRouter()

_PATIENT_WRITE_ROLES = ("receptionist", "assistant", "practitioner", "organization_admin")


@router.get("", response_model=list[PatientRead])
async def search_patients(
    user: AuthenticatedUser, session: DbSession, q: str | None = None
) -> list[PatientRead]:
    service = PatientService(PatientRepository(session))
    return await service.search(user.organization_id, q)


@router.post(
    "",
    response_model=PatientRead,
    status_code=201,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def create_patient(
    payload: PatientCreate, user: AuthenticatedUser, session: DbSession
) -> PatientRead:
    service = PatientService(PatientRepository(session))
    patient = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="patient.created",
        resource_type="patient",
        resource_id=str(patient.id),
    )
    await session.commit()
    return patient


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> PatientRead:
    service = PatientService(PatientRepository(session))
    return await service.get(user.organization_id, patient_id)


@router.get(
    "/{patient_id}/communication-preferences",
    response_model=PatientCommunicationPreferencesRead,
)
async def get_communication_preferences(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> PatientCommunicationPreferencesRead:
    patient = await PatientService(PatientRepository(session)).get(user.organization_id, patient_id)
    return PatientCommunicationPreferencesRead(
        patient_id=patient.id,
        phone_number=patient.phone_number,
        whatsapp_opt_out=patient.whatsapp_opt_out,
        whatsapp_opt_out_at=patient.whatsapp_opt_out_at,
        whatsapp_opt_in_at=patient.whatsapp_opt_in_at,
    )


@router.patch(
    "/{patient_id}/communication-preferences",
    response_model=PatientCommunicationPreferencesRead,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def update_communication_preferences(
    patient_id: uuid.UUID,
    payload: PatientCommunicationPreferencesUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> PatientCommunicationPreferencesRead:
    service = PatientService(PatientRepository(session))
    patient = await service.get(user.organization_id, patient_id)
    previous_value = patient.whatsapp_opt_out
    patient = await service.update_whatsapp_opt_out(
        user.organization_id, patient_id, payload.whatsapp_opt_out
    )
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="patient.whatsapp_opt_out.updated",
        resource_type="patient",
        resource_id=str(patient.id),
        metadata={
            "previous_value": previous_value,
            "whatsapp_opt_out": patient.whatsapp_opt_out,
        },
    )
    await session.commit()
    return PatientCommunicationPreferencesRead(
        patient_id=patient.id,
        phone_number=patient.phone_number,
        whatsapp_opt_out=patient.whatsapp_opt_out,
        whatsapp_opt_out_at=patient.whatsapp_opt_out_at,
        whatsapp_opt_in_at=patient.whatsapp_opt_in_at,
    )


@router.patch("/{patient_id}", response_model=PatientRead)
async def update_patient(
    patient_id: uuid.UUID, payload: PatientUpdate, user: AuthenticatedUser, session: DbSession
) -> PatientRead:
    service = PatientService(PatientRepository(session))
    patient = await service.update(user.organization_id, patient_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="patient.updated",
        resource_type="patient",
        resource_id=str(patient.id),
        metadata={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return patient


@router.get("/{patient_id}/contacts", response_model=list[PatientContactRead])
async def list_patient_contacts(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[PatientContactRead]:
    service = PatientContactService(PatientContactRepository(session), PatientRepository(session))
    return await service.list_for_patient(user.organization_id, patient_id)


@router.post(
    "/contacts",
    response_model=PatientContactRead,
    status_code=201,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def create_patient_contact(
    payload: PatientContactCreate, user: AuthenticatedUser, session: DbSession
) -> PatientContactRead:
    service = PatientContactService(PatientContactRepository(session), PatientRepository(session))
    contact = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="patient_contact.created",
        resource_type="patient_contact",
        resource_id=str(contact.id),
        metadata={"patient_id": str(contact.patient_id)},
    )
    await session.commit()
    return contact


@router.patch(
    "/contacts/{contact_id}",
    response_model=PatientContactRead,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def update_patient_contact(
    contact_id: uuid.UUID,
    payload: PatientContactUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> PatientContactRead:
    service = PatientContactService(PatientContactRepository(session), PatientRepository(session))
    contact = await service.update(user.organization_id, contact_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="patient_contact.updated",
        resource_type="patient_contact",
        resource_id=str(contact.id),
        metadata={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return contact


@router.delete(
    "/contacts/{contact_id}",
    status_code=204,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def delete_patient_contact(
    contact_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> None:
    service = PatientContactService(PatientContactRepository(session), PatientRepository(session))
    await service.delete(user.organization_id, contact_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="patient_contact.deleted",
        resource_type="patient_contact",
        resource_id=str(contact_id),
    )
    await session.commit()


@router.get("/{patient_id}/emergency-contacts", response_model=list[EmergencyContactRead])
async def list_emergency_contacts(
    patient_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> list[EmergencyContactRead]:
    service = EmergencyContactService(
        EmergencyContactRepository(session), PatientRepository(session)
    )
    return await service.list_for_patient(user.organization_id, patient_id)


@router.post(
    "/emergency-contacts",
    response_model=EmergencyContactRead,
    status_code=201,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def create_emergency_contact(
    payload: EmergencyContactCreate, user: AuthenticatedUser, session: DbSession
) -> EmergencyContactRead:
    service = EmergencyContactService(
        EmergencyContactRepository(session), PatientRepository(session)
    )
    contact = await service.create(user.organization_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="emergency_contact.created",
        resource_type="emergency_contact",
        resource_id=str(contact.id),
        metadata={"patient_id": str(contact.patient_id)},
    )
    await session.commit()
    return contact


@router.patch(
    "/emergency-contacts/{contact_id}",
    response_model=EmergencyContactRead,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def update_emergency_contact(
    contact_id: uuid.UUID,
    payload: EmergencyContactUpdate,
    user: AuthenticatedUser,
    session: DbSession,
) -> EmergencyContactRead:
    service = EmergencyContactService(
        EmergencyContactRepository(session), PatientRepository(session)
    )
    contact = await service.update(user.organization_id, contact_id, payload)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="emergency_contact.updated",
        resource_type="emergency_contact",
        resource_id=str(contact.id),
        metadata={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return contact


@router.delete(
    "/emergency-contacts/{contact_id}",
    status_code=204,
    dependencies=[Depends(require_roles(*_PATIENT_WRITE_ROLES))],
)
async def delete_emergency_contact(
    contact_id: uuid.UUID, user: AuthenticatedUser, session: DbSession
) -> None:
    service = EmergencyContactService(
        EmergencyContactRepository(session), PatientRepository(session)
    )
    await service.delete(user.organization_id, contact_id)
    await AuditService(session).record(
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        action="emergency_contact.deleted",
        resource_type="emergency_contact",
        resource_id=str(contact_id),
    )
    await session.commit()
