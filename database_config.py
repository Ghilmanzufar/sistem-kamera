import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()

# --- DATABASE CONNECTION ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sugity_camera_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "user")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================
# STRUKTUR TABEL (MODELS)
# ==============================================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)

    password = Column(String)
    role = Column(String)  # 'operator', 'pengawas', 'admin'
    fullname = Column(String)
    is_active = Column(Boolean, default=True)


class Transaction(Base):
    __tablename__ = "transactions"
    id_trans = Column(String, primary_key=True, index=True)
    part_no = Column(String, nullable=True)
    part_name = Column(String, nullable=True)
    lot_no = Column(String, nullable=True)
    unique_no = Column(String, nullable=True)
    target_qty = Column(Integer, default=10)
    qty_actual = Column(Integer, default=0)
    status = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

class InspectionLog(Base):
    __tablename__ = "inspection_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_trans = Column(String, index=True)
    part_no = Column(String, index=True)
    detection_status = Column(String)  # 'OK' or 'NG'
    image_path = Column(String, nullable=True)
    confidence_score = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

class PartRule(Base):
    __tablename__ = "part_rules"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    p_no = Column(String, index=True, nullable=False)
    sisi = Column(String, nullable=False) # e.g., 'Depan', 'Belakang'
    nama_komponen = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)

# Buat semua tabel jika belum ada
Base.metadata.create_all(bind=engine)
