from fastapi import APIRouter, Request, Depends, Query, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from nongzi.database import get_db
from nongzi.utils.helpers import format_currency
from nongzi.config import DATA_DIR, DATABASE_PATH, STORE_NAME, STORE_ADDRESS, STORE_PHONE, VERSION
import os as _os
import shutil
from datetime import datetime, timezone

router = APIRouter(prefix="/system", tags=["系统设置"])

from fastapi.templating import Jinja2Templates
from nongzi.config import BASE_DIR
_td = _os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=_td)
templates.env.filters["currency"] = format_currency

@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    """系统设置首页"""
    # Get system config
    config_items = {}
    try:
        from nongzi.models.system import SystemConfig
        configs = db.query(SystemConfig).all()
        config_items = {c.key: c.value for c in configs}
    except Exception:
        pass
    # List backups
    backup_dir = _os.path.join(DATA_DIR, "backups")
    backups = []
    if _os.path.exists(backup_dir):
        for f in sorted(_os.listdir(backup_dir), reverse=True):
            if f.endswith(".db"):
                fpath = _os.path.join(backup_dir, f)
                size_bytes = _os.path.getsize(fpath)
                size_mb = round(size_bytes / (1024 * 1024), 2)
                backups.append({"name": f, "size_mb": size_mb, "path": fpath})
    return templates.TemplateResponse("system/index.html", {
        "request": request,
        "config": config_items,
        "backups": backups[:10],
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "store_phone": STORE_PHONE,
        "version": VERSION,
    })

@router.post("/backup")
def backup_database(request: Request, db: Session = Depends(get_db)):
    """一键备份数据库"""
    backup_dir = _os.path.join(DATA_DIR, "backups")
    _os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"nongzi_backup_{timestamp}.db"
    backup_path = _os.path.join(backup_dir, backup_name)
    shutil.copy2(DATABASE_PATH, backup_path)
    size_mb = round(_os.path.getsize(backup_path) / (1024 * 1024), 2)
    return JSONResponse({"success": True, "message": "备份成功", "name": backup_name, "size_mb": size_mb})

@router.post("/restore")
async def restore_database(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """恢复数据库（上传.db文件）"""
    if not file.filename or not file.filename.endswith(".db"):
        return JSONResponse({"success": False, "message": "请上传.db格式的备份文件"})
    try:
        contents = await file.read()
        # Save current db as auto-backup first
        backup_dir = _os.path.join(DATA_DIR, "backups")
        _os.makedirs(backup_dir, exist_ok=True)
        auto_backup = _os.path.join(backup_dir, f"auto_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DATABASE_PATH, auto_backup)
        # Write uploaded file
        with open(DATABASE_PATH, "wb") as f:
            f.write(contents)
        return JSONResponse({"success": True, "message": "数据库恢复成功，请重启应用"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"恢复失败: {str(e)}"})

@router.post("/init-demo")
def init_demo_data(request: Request, db: Session = Depends(get_db)):
    """初始化演示数据（清空现有数据）"""
    try:
        from nongzi.utils.demo_data import load_demo_data
        load_demo_data(db)
        return JSONResponse({"success": True, "message": "演示数据初始化完成"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"初始化失败: {str(e)}"})

@router.post("/save-config")
async def save_config(request: Request, db: Session = Depends(get_db)):
    """保存系统配置"""
    try:
        from nongzi.models.system import SystemConfig
        form = await request.form()
        for key, value in form.items():
            cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if cfg:
                cfg.value = str(value)
            else:
                db.add(SystemConfig(key=key, value=str(value)))
        db.commit()
        return JSONResponse({"success": True, "message": "配置保存成功"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"保存失败: {str(e)}"})
