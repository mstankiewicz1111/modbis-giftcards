from sqlalchemy import Column, Integer, String
from database.session import Base


class GiftCode(Base):
    __tablename__ = "gift_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    value = Column(Integer, nullable=False)
    # numer seryjny zamówienia z Idosell (orderSerialNumber)
    order_id = Column(String, nullable=True, index=True)
