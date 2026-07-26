import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from medical_api.modules.consents.models import (
    ConsentAnswer,
    ConsentDocument,
    ConsentQuestion,
    ConsentQuestionOption,
    ConsentRequest,
    ConsentRule,
    ConsentSignature,
    ConsentSubmission,
    ConsentTemplateVersion,
)


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
