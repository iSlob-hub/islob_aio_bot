from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import BigInteger, DateTime, String, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Payment(Base):
    """Payment model for storing payment data"""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payed_weeks_left: Mapped[int] = mapped_column(Integer, nullable=False)

    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    user = relationship("User", back_populates="payments")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
