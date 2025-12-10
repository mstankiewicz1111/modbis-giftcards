from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from database.session import Base


class GiftCode(Base):
    __tablename__ = "gift_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    value = Column(Integer, nullable=False)
    # numer seryjny zamówienia z Idosell (orderSerialNumber)
    order_id = Column(String, nullable=True, index=True)


class WebhookEvent(Base):
    """
    Proste logi webhooków, do podglądu w panelu admina.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # np. 'order_webhook'
    status = Column(String, nullable=False, index=True)      # np. 'processed', 'ignored', 'error'
    message = Column(String, nullable=True)

    order_id = Column(String, nullable=True, index=True)
    order_serial = Column(String, nullable=True, index=True)

    payload = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
