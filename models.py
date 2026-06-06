from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String, nullable=False)
    email    = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=True)   # null for Google users
    source   = Column(String, default="email") # "email" or "google"
    picture  = Column(String, nullable=True)
    created  = Column(DateTime, server_default=func.now())