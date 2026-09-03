from sqlalchemy import Column,Integer,String,DateTime
from datetime import datetime
from database import base

class Payment(base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, nullable=False)
    payment_id = Column(String, unique=True, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    stock = Column(Integer, nullable=False)

class Order(base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class Bundle(base):
    __tablename__ = "bundles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    product_1_id = Column(Integer, nullable=False)
    product_2_id = Column(Integer, nullable=False)
    bundle_price = Column(Integer, nullable=False)
    status = Column(String, default="active")
class Recommendation(base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    product_id = Column(Integer, nullable=False)
    current_price = Column(Integer, nullable=False)
    suggested_price = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="pending")

class AuditLog(base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    product_id = Column(Integer, nullable=False)
    old_price = Column(Integer, nullable=True)
    new_price = Column(Integer, nullable=True)
    status = Column(String, nullable=False)
    reason = Column(String, nullable=False)