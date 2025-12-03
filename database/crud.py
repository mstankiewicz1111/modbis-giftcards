from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from .models import GiftCode

def get_free_code(db: Session, value: int):
    """
    Pobiera jeden wolny kod o zadanej wartości (100/200/300),
    blokując rekord (FOR UPDATE), żeby uniknąć duplikatów.
    """
    stmt = (
        select(GiftCode)
        .where(GiftCode.value == value)
        .where(GiftCode.is_used == False)
        .with_for_update()
        .limit(1)
    )
    result = db.execute(stmt).scalars().first()
    return result

def mark_code_used(db: Session, code: GiftCode, order_id: str):
    code.is_used = True
    code.used_by_order_id = order_id
    code.used_at = datetime.utcnow()
    db.add(code)
    db.commit()
    db.refresh(code)
    return code
