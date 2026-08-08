import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.consents.models import (
    ConsentAnswer,
    ConsentDocument,
    ConsentQuestion,
    ConsentQuestionOption,
    ConsentRequest,
    ConsentRequestStatus,
    ConsentRule,
    ConsentSignature,
    ConsentSubmission,
    ConsentTemplate,
    ConsentTemplateVersion,
    EligibilityResult,
)


class ConsentTemplateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_template(self, template: ConsentTemplate) -> ConsentTemplate:
        self.session.add(template)
        await self.session.flush()
        return template

    async def create_version(self, version: ConsentTemplateVersion) -> ConsentTemplateVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def create_question(self, question: ConsentQuestion) -> ConsentQuestion:
        self.session.add(question)
        await self.session.flush()
        return question

    async def create_option(self, option: ConsentQuestionOption) -> ConsentQuestionOption:
        self.session.add(option)
        await self.session.flush()
        return option

    async def get_template(
        self, organization_id: uuid.UUID, template_id: uuid.UUID
    ) -> ConsentTemplate | None:
        stmt = select(ConsentTemplate).where(
            ConsentTemplate.organization_id == organization_id, ConsentTemplate.id == template_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_templates(self, organization_id: uuid.UUID) -> list[ConsentTemplate]:
        stmt = (
            select(ConsentTemplate)
            .where(ConsentTemplate.organization_id == organization_id)
            .order_by(ConsentTemplate.name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_version(self, version_id: uuid.UUID) -> ConsentTemplateVersion | None:
        return await self.session.get(ConsentTemplateVersion, version_id)

    async def list_versions(self, template_id: uuid.UUID) -> list[ConsentTemplateVersion]:
        stmt = (
            select(ConsentTemplateVersion)
            .where(ConsentTemplateVersion.template_id == template_id)
            .order_by(ConsentTemplateVersion.version_number.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_version(self, template_id: uuid.UUID) -> ConsentTemplateVersion | None:
        versions = await self.list_versions(template_id)
        return versions[0] if versions else None


class ConsentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_request_by_token_hash(self, token_hash: str) -> ConsentRequest | None:
        stmt = select(ConsentRequest).where(ConsentRequest.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_template_version(
        self, template_version_id: uuid.UUID
    ) -> ConsentTemplateVersion | None:
        return await self.session.get(ConsentTemplateVersion, template_version_id)

    async def list_requests(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID | None = None,
        status: ConsentRequestStatus | None = None,
        needs_review: bool = False,
    ) -> list[ConsentRequest]:
        conditions = [ConsentRequest.organization_id == organization_id]
        if patient_id is not None:
            conditions.append(ConsentRequest.patient_id == patient_id)
        if status is not None:
            conditions.append(ConsentRequest.status == status)

        stmt = select(ConsentRequest)
        if needs_review:
            stmt = stmt.join(
                ConsentSubmission,
                ConsentSubmission.consent_request_id == ConsentRequest.id,
            )
            conditions.append(
                ConsentSubmission.eligibility_result == EligibilityResult.REQUIRES_MANUAL_REVIEW
            )

        stmt = stmt.where(*conditions).order_by(ConsentRequest.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_submission_by_request(
        self, consent_request_id: uuid.UUID
    ) -> ConsentSubmission | None:
        stmt = select(ConsentSubmission).where(
            ConsentSubmission.consent_request_id == consent_request_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_questions(self, template_version_id: uuid.UUID) -> list[ConsentQuestion]:
        stmt = (
            select(ConsentQuestion)
            .where(ConsentQuestion.template_version_id == template_version_id)
            .order_by(ConsentQuestion.display_order)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_options(self, question_id: uuid.UUID) -> list[ConsentQuestionOption]:
        stmt = select(ConsentQuestionOption).where(ConsentQuestionOption.question_id == question_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_rules(self, template_version_id: uuid.UUID) -> list[ConsentRule]:
        stmt = (
            select(ConsentRule)
            .where(ConsentRule.template_version_id == template_version_id)
            .order_by(ConsentRule.priority.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_submission(self, submission: ConsentSubmission) -> ConsentSubmission:
        self.session.add(submission)
        await self.session.flush()
        return submission

    async def get_submission(self, submission_id: uuid.UUID) -> ConsentSubmission | None:
        return await self.session.get(ConsentSubmission, submission_id)

    async def get_request(self, request_id: uuid.UUID) -> ConsentRequest | None:
        return await self.session.get(ConsentRequest, request_id)

    async def list_answers(self, submission_id: uuid.UUID) -> list[ConsentAnswer]:
        stmt = select(ConsentAnswer).where(ConsentAnswer.submission_id == submission_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_signature(self, submission_id: uuid.UUID) -> ConsentSignature | None:
        stmt = select(ConsentSignature).where(ConsentSignature.submission_id == submission_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_document(self, document: ConsentDocument) -> ConsentDocument:
        self.session.add(document)
        await self.session.flush()
        return document

    async def get_document_with_org_check(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> ConsentDocument | None:
        # ConsentDocument has no organization_id of its own — same
        # join-through-parent pattern as ClinicalNote/PatientMedicalHistory
        # (see "Complete server-side authorization review" in
        # missing_features.md), joined two levels up through Submission ->
        # Request since that's where organization_id actually lives.
        stmt = (
            select(ConsentDocument)
            .join(ConsentSubmission, ConsentSubmission.id == ConsentDocument.submission_id)
            .join(ConsentRequest, ConsentRequest.id == ConsentSubmission.consent_request_id)
            .where(
                ConsentDocument.id == document_id,
                ConsentRequest.organization_id == organization_id,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_current_document_for_submission(
        self, submission_id: uuid.UUID
    ) -> ConsentDocument | None:
        stmt = select(ConsentDocument).where(
            ConsentDocument.submission_id == submission_id, ConsentDocument.is_current.is_(True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_documents_for_submission(
        self, submission_id: uuid.UUID
    ) -> list[ConsentDocument]:
        stmt = (
            select(ConsentDocument)
            .where(ConsentDocument.submission_id == submission_id)
            .order_by(ConsentDocument.document_version)
        )
        return list((await self.session.execute(stmt)).scalars().all())
