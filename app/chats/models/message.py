from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Self
from uuid import UUID, uuid7

from sqlalchemy import (
    UUID as SAUUID,
    BigInteger,
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    TypeDecorator,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.chats.config import chat_config
from app.chats.exceptions import (
    AttachmentLimitExceededError,
    AttachmentNotFoundError,
    InvalidMessageError,
    MessageTooLongError,
)
from app.chats.models.attachment import AttachmentStatus, AttachmentType, MessageAttachment
from app.chats.models.profile import ChatUserProfile
from app.core.db.base_model import BaseModel, DateMixin
from app.core.events.event import BaseEvent
from app.core.utils import contains_link

if TYPE_CHECKING:
    from app.chats.models.chat import Chat


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    REPLY = "reply"
    FORWARD = "forward"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"

    @classmethod
    def for_attachments(cls, attachments: Iterable[MessageAttachment]) -> MessageType:
        kinds = {attachment.attachment_type for attachment in attachments}
        if AttachmentType.VOICE in kinds:
            return cls.VOICE

        if AttachmentType.VIDEO_NOTE in kinds:
            return cls.VIDEO_NOTE

        if kinds & {AttachmentType.IMAGE, AttachmentType.VIDEO}:
            return cls.IMAGE

        if AttachmentType.FILE in kinds:
            return cls.FILE

        return cls.TEXT


class SystemMessageAction(StrEnum):
    MESSAGE_PINNED = "message_pinned"


@dataclass(frozen=True)
class SendedMessageEvent(BaseEvent):
    message_id: str
    chat_id: str
    seq: int
    sender_id: int | None
    message_type: str
    notify: bool = True

    __event_name__ = "chats.message.sent"

    def get_aggregate_id(self) -> str:
        return str(self.chat_id)


@dataclass(frozen=True)
class ReadedMessageEvent(BaseEvent):
    chat_id: str
    seq: int
    reader_id: int

    __event_name__ = "chats.message.readed"

    def get_aggregate_id(self) -> str:
        return str(self.chat_id)


@dataclass(frozen=True)
class ModifiedMessageEvent(BaseEvent):
    message_id: str
    chat_id: str
    seq: int
    modified_by: int

    __event_name__ = "chats.message.modified"

    def get_aggregate_id(self) -> str:
        return str(self.chat_id)


@dataclass(frozen=True)
class DeletedMessageEvent(BaseEvent):
    message_id: str
    chat_id: str
    seq: int
    deleted_by: int

    __event_name__ = "chats.message.deleted"

    def get_aggregate_id(self) -> str:
        return str(self.chat_id)


@dataclass(frozen=True)
class PinnedMessageEvent(BaseEvent):
    chat_id: str
    message_id: str
    seq: int
    pinned_by: int
    pinned_at: str

    __event_name__ = "chats.message.pinned"

    def get_aggregate_id(self) -> str:
        return str(self.chat_id)


@dataclass(frozen=True)
class UnpinnedMessagesEvent(BaseEvent):
    chat_id: str
    message_ids: list[str]
    unpinned_by: int
    all: bool = False

    __event_name__ = "chats.message.unpinned"

    def get_aggregate_id(self) -> str:
        return str(self.chat_id)


class MessageBlockType(StrEnum):
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    CODE = "code"
    PRE = "pre"
    TEXT_LINK = "text_link"
    URL = "url"
    SPOILER = "spoiler"
    MENTION = "mention"
    CUSTOM_EMOJI = "custom_emoji"


@dataclass(frozen=True, slots=True)
class MessageBlock:
    offset: int
    length: int


@dataclass(frozen=True, slots=True)
class BoldBlock(MessageBlock):
    pass


@dataclass(frozen=True, slots=True)
class ItalicBlock(MessageBlock):
    pass


@dataclass(frozen=True, slots=True)
class UnderlineBlock(MessageBlock):
    pass


@dataclass(frozen=True, slots=True)
class StrikethroughBlock(MessageBlock):
    pass


@dataclass(frozen=True, slots=True)
class CodeBlock(MessageBlock):
    pass


@dataclass(frozen=True, slots=True)
class PreBlock(MessageBlock):
    program_language: str | None = None


@dataclass(frozen=True, slots=True)
class TextLinkBlock(MessageBlock):
    url: str


@dataclass(frozen=True, slots=True)
class UrlBlock(MessageBlock):
    pass


@dataclass(frozen=True, slots=True)
class SpoilerBlock(MessageBlock):
    pass


@dataclass(frozen=True, slots=True)
class MentionBlock(MessageBlock):
    username: str


@dataclass(frozen=True, slots=True)
class CustomEmojiBlock(MessageBlock):
    emoji_id: str


MESSAGE_BLOCK_CLASSES: dict[MessageBlockType, type[MessageBlock]] = {
    MessageBlockType.BOLD: BoldBlock,
    MessageBlockType.ITALIC: ItalicBlock,
    MessageBlockType.UNDERLINE: UnderlineBlock,
    MessageBlockType.STRIKETHROUGH: StrikethroughBlock,
    MessageBlockType.CODE: CodeBlock,
    MessageBlockType.PRE: PreBlock,
    MessageBlockType.TEXT_LINK: TextLinkBlock,
    MessageBlockType.URL: UrlBlock,
    MessageBlockType.SPOILER: SpoilerBlock,
    MessageBlockType.MENTION: MentionBlock,
    MessageBlockType.CUSTOM_EMOJI: CustomEmojiBlock,
}


class MessageBlocksType(TypeDecorator):
    impl = JSONB
    cache_ok = True

    def process_bind_param(
        self,
        value: list[MessageBlock] | None,
        _dialect: Any,
    ) -> list[dict[str, Any]]:
        if value is None:
            return []

        result = []

        for block in value:
            block_type = type(block)

            block_name = next(
                (
                    name
                    for name, cls in MESSAGE_BLOCK_CLASSES.items()
                    if cls is block_type
                ),
                None,
            )

            if block_name is None:
                raise ValueError(f"Unknown message block: {block_type}")

            result.append({
                "type": block_name.value,
                **asdict(block),
            })

        return result

    def process_result_value(
        self,
        value: list[dict[str, Any]] | None,
        _dialect: Any,
    ) -> list[MessageBlock]:
        if value is None:
            return []

        result = []

        for item in value:
            item = item.copy()

            block_type = MessageBlockType(item.pop("type"))
            block_class = MESSAGE_BLOCK_CLASSES[block_type]

            result.append(block_class(**item))

        return result


class Message(BaseModel, DateMixin):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(SAUUID(as_uuid=True), nullable=False, primary_key=True)

    chat_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(BigInteger, default=0)

    author_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    type: Mapped[MessageType] = mapped_column(
        SAEnum(MessageType), default=MessageType.TEXT, nullable=False
    )
    content: Mapped[str | None] = mapped_column(String(chat_config.MAX_MESSAGE_LENGTH))
    blocks: Mapped[list[MessageBlock]] = mapped_column(MessageBlocksType, nullable=False, default=list)

    reply_to_id: Mapped[UUID | None] = mapped_column(
        SAUUID, ForeignKey("messages.id"), nullable=True
    )

    forwarded_from_chat_id: Mapped[UUID | None] = mapped_column(
        SAUUID, ForeignKey("chats.id", ondelete="SET NULL"), nullable=True
    )
    forwarded_from_message_id: Mapped[UUID | None] = mapped_column(
        SAUUID, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    forwarded_from_author_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    action: Mapped[SystemMessageAction | None] = mapped_column(
        SAEnum(SystemMessageAction, native_enum=False, length=32), nullable=True, default=None
    )

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_links: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    chat: Mapped[Chat] = relationship(back_populates="messages", foreign_keys=[chat_id], lazy="noload")
    reply_to: Mapped[Message | None] = relationship(
        foreign_keys=[reply_to_id], remote_side="Message.id", lazy="noload"
    )
    forwarded_from: Mapped[Message | None] = relationship(
        foreign_keys=[forwarded_from_message_id], remote_side="Message.id", lazy="noload"
    )
    attachments: Mapped[list[MessageAttachment]] = relationship(
        lazy="noload", cascade="all, delete-orphan", order_by=MessageAttachment.id
    )
    profile: Mapped[ChatUserProfile | None] = relationship(
        ChatUserProfile,
        foreign_keys=[author_id],
        primaryjoin="Message.author_id == ChatUserProfile.user_id",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_messages_chat_not_deleted", "chat_id", "seq",
              postgresql_where="is_deleted = false"),
        Index(
            "idx_messages_content_tsvector",
            text("to_tsvector('simple', content)"),
            postgresql_using="gin",
        ),
        Index(
            "ix_messages_chat_links",
            "chat_id", "seq",
            postgresql_where=text("has_links AND is_deleted = false"),
        ),
    )

    @classmethod
    def create(
        cls,
        sender_id: int | None,
        chat_id: UUID,
        seq: int,
        content: str | None,
        reply_to_id: UUID | None = None,
        message_type: MessageType = MessageType.TEXT,
        forwarded_from_chat_id: UUID | None = None,
        forwarded_from_message_id: UUID | None = None,
        forwarded_from_author_id: int | None=None,
        attachments: list[MessageAttachment] | None = None,
        notify: bool = True,
        action: SystemMessageAction | None = None,
    ) -> Self:
        if message_type == MessageType.REPLY and reply_to_id is None:
            raise InvalidMessageError(reason="reply_to_id is required for reply messages")

        instance = cls(
            id=uuid7(),
            author_id=sender_id,
            chat_id=chat_id,
            seq=seq,
            content=content,
            reply_to_id=reply_to_id,
            type=message_type,
            forwarded_from_chat_id=forwarded_from_chat_id,
            forwarded_from_message_id=forwarded_from_message_id,
            forwarded_from_author_id=forwarded_from_author_id,
            action=action,
            has_links=contains_link(content),
        )

        instance.validate_content()

        if attachments is not None:
            for attachment in attachments:
                attachment.bind_to_message(seq)
            instance.attachments.extend(attachments)

        if attachments is not None or message_type in (
            MessageType.VOICE, MessageType.VIDEO_NOTE
        ):
            instance.validate_attachments()

        instance.register_event(SendedMessageEvent(
            message_id=str(instance.id),
            chat_id=str(instance.chat_id),
            seq=instance.seq,
            sender_id=instance.author_id,
            message_type=message_type.value,
            notify=notify,
        ))

        return instance

    @classmethod
    def create_system(
        cls,
        actor_id: int,
        chat_id: UUID,
        seq: int,
        action: SystemMessageAction,
        reply_to_id: UUID | None = None,
    ) -> Self:
        return cls.create(
            sender_id=actor_id,
            chat_id=chat_id,
            seq=seq,
            content=None,
            reply_to_id=reply_to_id,
            message_type=MessageType.SYSTEM,
            action=action,
        )

    @classmethod
    def create_forward(
        cls,
        source: Message,
        sender_id: int,
        chat_id: UUID,
        seq: int,
        hide_author: bool = False,
        notify: bool = True,
    ) -> Self:
        attachments = source.forwardable_attachments(chat_id)

        if hide_author:
            return cls.create(
                sender_id=sender_id,
                chat_id=chat_id,
                seq=seq,
                content=source.content,
                message_type=source.copy_type(),
                attachments=attachments,
                notify=notify,
            )

        is_forward = source.type == MessageType.FORWARD
        return cls.create(
            sender_id=sender_id,
            chat_id=chat_id,
            seq=seq,
            content=source.content,
            message_type=MessageType.FORWARD,
            forwarded_from_chat_id=source.forwarded_from_chat_id if is_forward else source.chat_id,
            forwarded_from_message_id=source.forwarded_from_message_id if is_forward else source.id,
            forwarded_from_author_id=source.forwarded_from_author_id if is_forward else source.author_id,
            attachments=attachments,
            notify=notify,
        )

    def forwardable_attachments(self, chat_id: UUID) -> list[MessageAttachment]:
        return [
            attachment.create_for_forward(chat_id=chat_id)
            for attachment in sorted(self.attachments, key=lambda item: item.id)
            if attachment.attachment_status == AttachmentStatus.SUCCESS
        ]

    @property
    def is_forwardable(self) -> bool:
        if self.is_deleted or self.type == MessageType.SYSTEM:
            return False

        return bool(self.content) or any(
            attachment.attachment_status == AttachmentStatus.SUCCESS
            for attachment in self.attachments
        )

    def copy_type(self) -> MessageType:
        if self.type not in (MessageType.REPLY, MessageType.FORWARD):
            return self.type

        return MessageType.for_attachments(
            attachment
            for attachment in self.attachments
            if attachment.attachment_status == AttachmentStatus.SUCCESS
        )

    def update_content(self, new_content: str, modified_by: int) -> None:
        self.content = new_content
        self.is_edited = True
        self.has_links = contains_link(new_content)
        self.validate_content()
        self.register_event(
            ModifiedMessageEvent(
                message_id=str(self.id),
                chat_id=str(self.chat_id),
                seq=self.seq,
                modified_by=modified_by
            )
        )

    def delete(self, deleted_by: int) -> None:
        self.is_deleted = True
        self.register_event(
            DeletedMessageEvent(
                message_id=str(self.id),
                chat_id=str(self.chat_id),
                seq=self.seq,
                deleted_by=deleted_by
            )
        )

    def unpin(self, unpinned_by: int) -> None:
        self.register_event(
            UnpinnedMessagesEvent(
                chat_id=str(self.chat_id),
                message_ids=[str(self.id)],
                unpinned_by=unpinned_by,
            )
        )

    def validate_content(self) -> None:
        if not self.content:
            return

        if len(self.content) > chat_config.MAX_MESSAGE_LENGTH:
            raise MessageTooLongError(
                length=len(self.content),
                max_length=chat_config.MAX_MESSAGE_LENGTH
            )

        if "\x00" in self.content:
            raise InvalidMessageError(reason="message content contains null byte")

    def validate_attachments(self) -> None:
        media_count = sum(
            1 for a in self.attachments if a.attachment_type in (AttachmentType.IMAGE, AttachmentType.VIDEO)
        )
        file_count = sum(1 for a in self.attachments if a.attachment_type == AttachmentType.FILE)
        voice_count = sum(1 for a in self.attachments if a.attachment_type == AttachmentType.VOICE)
        video_note_count = sum(
            1 for a in self.attachments if a.attachment_type == AttachmentType.VIDEO_NOTE
        )
        exclusive_count = voice_count + video_note_count

        success = all(a.attachment_status == AttachmentStatus.SUCCESS for a in self.attachments)

        if media_count > chat_config.MAX_MEDIA_PER_MESSAGE:
            raise AttachmentLimitExceededError(count=media_count)
        if file_count > chat_config.MAX_FILES_PER_MESSAGE:
            raise AttachmentLimitExceededError(count=file_count)

        if exclusive_count > 1:
            raise AttachmentLimitExceededError(count=exclusive_count)
        if exclusive_count and (media_count or file_count):
            raise AttachmentLimitExceededError(
                count=exclusive_count + media_count + file_count
            )

        if self.type == MessageType.VOICE and voice_count != 1:
            raise InvalidMessageError(
                reason="voice message requires exactly one voice attachment"
            )
        if self.type == MessageType.VIDEO_NOTE and video_note_count != 1:
            raise InvalidMessageError(
                reason="video_note message requires exactly one video_note attachment"
            )
        if exclusive_count and self.type not in (
            MessageType.VOICE, MessageType.VIDEO_NOTE, MessageType.FORWARD
        ):
            raise InvalidMessageError(
                reason="voice/video_note attachment requires matching message_type"
            )

        if success is False:
            raise AttachmentNotFoundError(attachment_id="")
