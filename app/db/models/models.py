import enum
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, JSON, Enum as SQLEnum, Float, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=False)
    organization = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)

    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user")


class APIKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    user_id = Column(ForeignKey("users.id"), nullable=False)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    key_prefix = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    rate_limit_tier = Column(String, default="standard")

    user = relationship("User", back_populates="api_keys")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    user_id = Column(ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    input_file_url = Column(String)
    output_file_url = Column(String)
    progress_percent = Column(Integer, default=0)
    error_message = Column(String)
    full_text = Column(Text, nullable=True)  # New column for extracted text with placeholders

    user = relationship("User", back_populates="jobs")
    documents = relationship("Document", back_populates="job", cascade="all, delete-orphan")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    job_id = Column(ForeignKey("jobs.id"), nullable=False)
    page_number = Column(Integer)
    image_crop_url = Column(String)

    job = relationship("Job", back_populates="documents")
    tables = relationship("Table", back_populates="document", cascade="all, delete-orphan")


class Table(Base, TimestampMixin):
    __tablename__ = "tables"

    document_id = Column(ForeignKey("documents.id"), nullable=False)
    structure_json = Column(JSON)
    cleaned_data = Column(JSON)
    confidence_score = Column(Float)
    requires_review = Column(Boolean, default=False)

    document = relationship("Document", back_populates="tables")


class UsageLog(Base, TimestampMixin):
    __tablename__ = "usage_logs"

    api_key_id = Column(ForeignKey("api_keys.id"), nullable=False)
    endpoint = Column(String)
    tokens_consumed = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    user_id = Column(ForeignKey("users.id"), nullable=True)
    action = Column(String)
    ip_address = Column(String)
    status_code = Column(Integer)