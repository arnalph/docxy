import uuid
from sqlalchemy import Column, DateTime, func, Uuid
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    @declared_attr
    def id(cls):
        # Use generic Uuid which works across backends (as CHAR(32) or native UUID)
        return Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def updated_at(cls):
        return Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
