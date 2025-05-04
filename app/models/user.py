from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import BigInteger, DateTime, String, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    """User model for storing Telegram user data"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Conversation state
    current_node: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
