from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func
from datetime import datetime
from app.core.database import Base

class ViettelPostStatusLog(Base):
    __tablename__ = "viettelpost_status_logs"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    status_code = Column(String(50))
    status_message = Column(String(255))
    timestamp = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

