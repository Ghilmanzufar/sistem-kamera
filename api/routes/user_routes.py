from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, User, hash_password, log_audit_event
from api.auth import get_current_user_name

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    fullname: str
    is_active: bool = True

class UserUpdate(BaseModel):
    username: str
    password: Optional[str] = None
    role: str
    fullname: str
    is_active: bool = True

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    db_user = User(
        username=user.username,
        password=hash_password(user.password),
        role=user.role,
        fullname=user.fullname,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    log_audit_event(db, uname, "CREATE_USER", f"Membuat user baru: {user.username} ({user.fullname}, Role: {user.role.upper()})")
    return db_user

@router.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user.username
    if user.password:
        db_user.password = hash_password(user.password)
    db_user.role = user.role
    db_user.fullname = user.fullname
    db_user.is_active = user.is_active
    db.commit()
    db.refresh(db_user)
    log_audit_event(db, uname, "UPDATE_USER", f"Mengubah data user {user.username} (Role: {user.role.upper()})")
    return db_user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    target_username = db_user.username
    db.delete(db_user)
    db.commit()
    log_audit_event(db, uname, "DELETE_USER", f"Menghapus user {target_username} (ID: #{user_id})")
    return {"status": "ok"}
