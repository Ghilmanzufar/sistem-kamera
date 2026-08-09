import os
import shutil
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from database import get_db, log_audit_event
from api.auth import get_current_user_name
from core import model_cache
from ultralytics import YOLO

router = APIRouter()
WEIGHTS_DIR = os.path.join(os.getcwd(), "weights")

@router.get("/models")
def list_models():
    if not os.path.exists(WEIGHTS_DIR):
        return []
    files = [f for f in os.listdir(WEIGHTS_DIR) if f.endswith(('.pt', '.onnx', '.engine'))]
    result = []
    for f in files:
        f_path = os.path.join(WEIGHTS_DIR, f)
        size_mb = os.path.getsize(f_path) / (1024 * 1024)
        mtime = os.path.getmtime(f_path)
        result.append({
            "filename": f,
            "size_mb": round(size_mb, 2),
            "modified_time": mtime,
            "is_default": (f == "yolov8n.pt" or f == "yolov8n.onnx")
        })
    return sorted(result, key=lambda x: x["modified_time"], reverse=True)

@router.post("/models/upload")
async def upload_model(
    file: UploadFile = File(...), 
    part_no: str = Form(...),
    db: Session = Depends(get_db),
    uname: str = Depends(get_current_user_name)
):
    """Unggah file bobot model (.pt/.onnx) dengan validasi arsitektur YOLOv8."""
    if not (file.filename.endswith(".pt") or file.filename.endswith(".onnx")):
        raise HTTPException(status_code=400, detail="Format file harus berekstensi .pt atau .onnx")

    ext = ".onnx" if file.filename.endswith(".onnx") else ".pt"
    clean_pno = part_no.strip()
    dest_filename = f"{clean_pno}{ext}" if clean_pno else file.filename
    dest_path = os.path.join(WEIGHTS_DIR, dest_filename)
    
    if not os.path.exists(WEIGHTS_DIR):
        os.makedirs(WEIGHTS_DIR)

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    labels_found = []
    if ext == ".pt":
        try:
            test_model = YOLO(tmp_path, verbose=False)
            labels_found = list(test_model.names.values()) if hasattr(test_model, 'names') else []
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise HTTPException(status_code=400, detail=f"File bukan model YOLO yang valid: {str(e)}")

    shutil.move(tmp_path, dest_path)
    model_cache.clear()
    log_audit_event(db, uname, "UPLOAD_MODEL", f"Mengunggah model {dest_filename} untuk part {clean_pno} (Labels: {', '.join(labels_found[:5])})")
    
    return {
        "message": f"Model {dest_filename} berhasil diunggah!",
        "filename": dest_filename,
        "labels": labels_found
    }

@router.post("/models/inspect-labels")
async def inspect_labels(file: UploadFile = File(...)):
    """Memeriksa daftar kelas / label yang terkandung dalam file bobot .pt."""
    if not file.filename.endswith(".pt"):
        return {"labels": [], "message": "Pemeriksaan label otomatis hanya didukung untuk format PyTorch .pt"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pt") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        test_model = YOLO(tmp_path, verbose=False)
        labels = list(test_model.names.values()) if hasattr(test_model, 'names') else []
        return {"labels": labels, "count": len(labels)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca label model: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.delete("/models/{filename}")
def delete_model(filename: str, db: Session = Depends(get_db), uname: str = Depends(get_current_user_name)):
    file_path = os.path.join(WEIGHTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    os.remove(file_path)
    model_cache.clear()
    log_audit_event(db, uname, "DELETE_MODEL", f"Menghapus file model: {filename}")
    return {"message": f"Model {filename} berhasil dihapus"}
