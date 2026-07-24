import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# --- SYSTEM SETTINGS ---
MODEL_CACHE = True
SAVE_IMAGE = False
TIMEOUT = 60
DEFAULT_PIN = "1234"
_cam_env = os.getenv("CAMERA_ID", "0")
CAMERA_ID = int(_cam_env) if _cam_env.isdigit() else _cam_env

# --- JWT SETTINGS ---
SECRET_KEY = os.getenv("SECRET_KEY", "sugity_super_secret_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

# --- DATABASE CONNECTION ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sugity_camera_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Ghilmanlove.21")

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
    detection_status = Column(String)  # 'OK' or 'NG'
    confidence_score = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class PartRule(Base):
    __tablename__ = "part_rules"
    p_no = Column(String, primary_key=True, index=True)
    tipe_cek = Column(String, nullable=False)
    aturan_sisi = Column(JSON, nullable=False)
