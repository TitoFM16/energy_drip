"""Idempotent development seed: demo patients, a practitioner, a treatment
catalogue entry, availability, and a published consent template with a
working eligibility rule set.

Distinct from `bootstrap_clinic.py`: that script creates the one clinic and
its first admin — the real, one-time production bootstrap. This script only
adds obviously-fake demonstration data on top of an already-bootstrapped
clinic, refuses to run in production, and is safe to re-run — every entity
is looked up by a fixed "seed" identifier before being created, so running
it twice does not duplicate data.

Usage (clinic must already be bootstrapped — see bootstrap_clinic.py):
    uv run python scripts/seed_reference_data.py
"""

import asyncio
import sys
import uuid
from datetime import UTC, datetime, time

from medical_api.core.config import get_settings
from medical_api.core.database import async_session_factory
from medical_api.core.security import hash_password
from medical_api.modules.consents.models import (
    ConsentQuestion,
    ConsentQuestionOption,
    ConsentRule,
    ConsentTemplate,
    ConsentTemplateVersion,
    EligibilityResult,
    QuestionType,
)
from medical_api.modules.consents.repository import ConsentTemplateRepository
from medical_api.modules.identity.models import RoleName, User
from medical_api.modules.identity.repository import UserRepository
from medical_api.modules.organizations.repository import OrganizationRepository
from medical_api.modules.patients.models import Patient
from medical_api.modules.patients.repository import PatientRepository
from medical_api.modules.scheduling.models import AvailabilityRule, Practitioner
from medical_api.modules.scheduling.repository import AvailabilityRepository, PractitionerRepository
from medical_api.modules.treatments.models import TreatmentDefinition
from medical_api.modules.treatments.repository import TreatmentDefinitionRepository

# Fixed identifiers used purely to detect "have we already seeded this?" on
# a re-run — not meant to look realistic.
SEED_PRACTITIONER_EMAIL = "demo.practitioner@example.io"
SEED_PATIENT_DOCUMENT_IDS = ["SEED-PATIENT-1", "SEED-PATIENT-2"]
SEED_TREATMENT_NAME = "Limpieza facial (demo)"
SEED_TEMPLATE_NAME = "Consentimiento de limpieza facial (demo)"

settings = get_settings()


async def seed() -> None:
    async with async_session_factory() as session:
        organizations = OrganizationRepository(session)
        organization = await organizations.get_first()
        if organization is None:
            print("No organization found. Run scripts/bootstrap_clinic.py first.")
            sys.exit(1)
        organization_id = organization.id

        users = UserRepository(session)
        practitioner_user = await users.get_by_email(organization_id, SEED_PRACTITIONER_EMAIL)
        if practitioner_user is None:
            practitioner_user = User(
                organization_id=organization_id,
                email=SEED_PRACTITIONER_EMAIL,
                hashed_password=hash_password(uuid.uuid4().hex),
                full_name="Demo Practitioner",
            )
            await users.create(practitioner_user)
            role = await users.get_or_create_role(RoleName.PRACTITIONER)
            await users.assign_role(practitioner_user.id, role.id)
            print(f"Created demo practitioner user {SEED_PRACTITIONER_EMAIL}")
        else:
            print(f"Demo practitioner user {SEED_PRACTITIONER_EMAIL} already exists")

        practitioners = PractitionerRepository(session)
        practitioner = await practitioners.get_by_user_id(organization_id, practitioner_user.id)
        if practitioner is None:
            practitioner = Practitioner(
                organization_id=organization_id,
                user_id=practitioner_user.id,
                specialty="Estética facial",
            )
            await practitioners.create(practitioner)
            print("Created demo practitioner profile")
        else:
            print("Demo practitioner profile already exists")

        availability = AvailabilityRepository(session)
        existing_rules = await availability.list_rules(organization_id, practitioner.id)
        existing_weekdays = {rule.weekday for rule in existing_rules}
        created_rules = 0
        for weekday in range(5):  # Monday-Friday
            if weekday in existing_weekdays:
                continue
            await availability.create_rule(
                AvailabilityRule(
                    organization_id=organization_id,
                    practitioner_id=practitioner.id,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
            )
            created_rules += 1
        print(
            f"Created {created_rules} availability rule(s)"
            if created_rules
            else "Availability rules already exist"
        )

        patients = PatientRepository(session)
        seed_patients = [
            ("Ana", "Pérez", SEED_PATIENT_DOCUMENT_IDS[0], "+573001112233"),
            ("Carlos", "Ramírez", SEED_PATIENT_DOCUMENT_IDS[1], "+573004445566"),
        ]
        created_patients = 0
        for first_name, last_name, document_id, phone_number in seed_patients:
            existing = await patients.search(organization_id, document_id)
            if any(p.document_id == document_id for p in existing):
                continue
            await patients.create(
                Patient(
                    organization_id=organization_id,
                    first_name=first_name,
                    last_name=last_name,
                    document_id=document_id,
                    phone_number=phone_number,
                )
            )
            created_patients += 1
        print(
            f"Created {created_patients} demo patient(s)"
            if created_patients
            else "Demo patients already exist"
        )

        treatment_definitions = TreatmentDefinitionRepository(session)
        existing_treatments = await treatment_definitions.list_all(
            organization_id, include_inactive=True
        )
        if not any(t.name == SEED_TREATMENT_NAME for t in existing_treatments):
            await treatment_definitions.create(
                TreatmentDefinition(
                    organization_id=organization_id,
                    name=SEED_TREATMENT_NAME,
                    description="Tratamiento de demostración para desarrollo local.",
                    default_session_count=4,
                )
            )
            print(f"Created treatment catalogue entry '{SEED_TREATMENT_NAME}'")
        else:
            print(f"Treatment catalogue entry '{SEED_TREATMENT_NAME}' already exists")

        templates = ConsentTemplateRepository(session)
        existing_templates = await templates.list_templates(organization_id)
        if not any(t.name == SEED_TEMPLATE_NAME for t in existing_templates):
            template = ConsentTemplate(organization_id=organization_id, name=SEED_TEMPLATE_NAME)
            await templates.create_template(template)

            version = ConsentTemplateVersion(
                template_id=template.id,
                version_number=1,
                body_markdown=(
                    "Autorizo el procedimiento de limpieza facial y confirmo haber respondido "
                    "el filtro médico con información veraz."
                ),
                # Published immediately: this is throwaway demo data, not a
                # real draft awaiting review, and staff-web's "Solicitar
                # consentimiento" picker only offers published versions.
                published_at=datetime.now(UTC),
            )
            await templates.create_version(version)

            pregnant_question = ConsentQuestion(
                template_version_id=version.id,
                field_key="pregnant",
                prompt="¿Estás embarazada?",
                question_type=QuestionType.BOOLEAN,
                display_order=0,
                is_required=True,
            )
            await templates.create_question(pregnant_question)

            allergies_question = ConsentQuestion(
                template_version_id=version.id,
                field_key="allergies",
                prompt="¿Tienes alergias conocidas?",
                question_type=QuestionType.TEXT,
                display_order=1,
                is_required=False,
            )
            await templates.create_question(allergies_question)
            await templates.create_option(
                ConsentQuestionOption(question_id=pregnant_question.id, value="true", label="Sí")
            )
            await templates.create_option(
                ConsentQuestionOption(question_id=pregnant_question.id, value="false", label="No")
            )

            # A working eligibility rule set — the UI has no rule authoring
            # form yet (see docs/missing_features.md), so this is currently
            # the only way to see the eligibility engine produce `eligible`
            # and `not_eligible` results instead of every submission falling
            # through to `requires_manual_review`.
            session.add(
                ConsentRule(
                    template_version_id=version.id,
                    rule={"field": "pregnant", "operator": "equals", "value": True},
                    result=EligibilityResult.NOT_ELIGIBLE,
                    priority=10,
                )
            )
            session.add(
                ConsentRule(
                    template_version_id=version.id,
                    rule={"field": "pregnant", "operator": "equals", "value": False},
                    result=EligibilityResult.ELIGIBLE,
                    priority=5,
                )
            )
            await session.flush()

            print(f"Created and published consent template '{SEED_TEMPLATE_NAME}' with 2 rules")
        else:
            print(f"Consent template '{SEED_TEMPLATE_NAME}' already exists")

        await session.commit()


def main() -> None:
    if settings.is_production:
        print("Refusing to seed demonstration data in production.")
        sys.exit(1)
    asyncio.run(seed())


if __name__ == "__main__":
    main()
