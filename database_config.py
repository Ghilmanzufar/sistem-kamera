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
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

import hashlib
import secrets

def hash_password(password: str) -> str:
    if password.startswith("pbkdf2:"):
        return password
    salt = secrets.token_hex(8)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"pbkdf2:{salt}:{hashed}"

def verify_password(plain: str, stored: str) -> bool:
    if not stored:
        return False
    if not stored.startswith("pbkdf2:"):
        # 👱 Ponytail ceiling: Backward compatibility untuk password lama tipe plaintext
        return plain == stored
    parts = stored.split(":")
    if len(parts) != 3:
        return False
    _, salt, hashed = parts
    check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100000).hex()
    return secrets.compare_digest(check, hashed)

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
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

class CameraConfig(Base):
    __tablename__ = "camera_configs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    source = Column(String) # '0', '1', or RTSP url
    is_active = Column(Boolean, default=False)

class PartRule(Base):
    __tablename__ = "part_rules"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    p_no = Column(String, index=True, nullable=False)
    sisi = Column(String, default="-") # e.g., 'Depan', 'Belakang' atau '-'
    nama_komponen = Column(String, nullable=False)
    qty = Column(Integer, default=1)
    min_confidence = Column(Float, default=0.70)
    avg_confidence = Column(Float, default=0.75)
    min_coverage = Column(Float, default=1.0)

class GlobalSettings(Base):
    __tablename__ = "global_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    default_avg_conf = Column(Float, default=0.75)
    default_min_conf = Column(Float, default=0.70)
    default_min_coverage = Column(Float, default=1.0)

class SisonConfig(Base):
    __tablename__ = "sison_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    callback_url = Column(String, default="http://localhost:3000/api/kamera/callback")
    api_key = Column(String, default="kamera-secret-key")  # ponytail: upgrade ke random UUID jika perlu

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now())
    username = Column(String, index=True, default="SYSTEM")
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)

def log_audit_event(db, username: str, action: str, details: str = ""):
    """Helper untuk mencatat aktivitas sistem / user ke database audit_logs."""
    try:
        log = AuditLog(username=username or "SYSTEM", action=action, details=details)
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Gagal mencatat log '{action}': {e}")

# Buat semua tabel jika belum ada
Base.metadata.create_all(bind=engine)

# 👱 Ponytail: Seeding default pengawas & migrasi otomatis role admin lama
def _seed_default_users():
    try:
        with SessionLocal() as db:
            # 1. Migrasi user lama yang masih ber-role 'admin' menjadi 'pengawas'
            admins = db.query(User).filter(User.role == "admin").all()
            if admins:
                for a in admins:
                    a.role = "pengawas"
                db.commit()
                print(f"[SYSTEM] Auto-migrated {len(admins)} user(s) from 'admin' role to 'pengawas'.")

            # 2. Seed default user pengawas jika database masih kosong
            if not db.query(User).first():
                default_pengawas = User(
                    username="pengawas",
                    password=hash_password("1234"),
                    role="pengawas",
                    fullname="Default Pengawas",
                    is_active=True
                )
                db.add(default_pengawas)
                db.commit()
                print("[SYSTEM] Default pengawas seeded (username: pengawas, pin: 1234). Harap segera sesuaikan PIN di Web Admin.")
    except Exception as e:
        print(f"[WARN] Gagal seeding/migrasi default user: {e}")

_seed_default_users()

