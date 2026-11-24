from dishka_faststream import FromDishka, inject
from faststream.kafka import KafkaRouter
from pydantic import BaseModel

from app.chats.commands.contacts.apply import ApplyUserContactCommand
from app.chats.config import chat_config
from app.core.consumers.event import DictEventDTO
from app.core.consumers.idempotency import EventIdempotencyGuard
from app.core.mediators.base import BaseMediator

router = KafkaRouter()

CONTACT_EVENT_STATES: dict[str, bool] = {
    chat_config.CONTACT_ADDED_EVENT: True,
    chat_config.CONTACT_REMOVED_EVENT: False,
}


class UserContactPayload(BaseModel):
    owner_id: int
    contact_id: int


@router.subscriber(
    chat_config.PROFILE_TOPIC,
    group_id=chat_config.CONTACTS_PROJECTION_GROUP_ID,
)
@inject
async def project_user_contact(
    event: DictEventDTO,
    mediator: FromDishka[BaseMediator],
    idempotency: FromDishka[EventIdempotencyGuard],
) -> None:
    added = CONTACT_EVENT_STATES.get(event.event_name)
    if added is None:
        return

    payload = UserContactPayload.model_validate(event.payload)

    await idempotency.execute(
        group=chat_config.BLOCK_PROJECTION_GROUP_ID,
        event_id=event.event_id,
        callback=lambda: mediator.handle_command(
            ApplyUserContactCommand(
                owner_id=payload.owner_id,
                contact_id=payload.contact_id,
                added=added,
            )
        )
    )
