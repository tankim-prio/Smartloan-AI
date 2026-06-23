from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExtractedText(Base):
    __tablename__ = "extracted_texts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("application_documents.id"),
        nullable=True,
        index=True,
    )

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
