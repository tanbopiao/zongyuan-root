#!/usr/bin/env python3
"""
媒体归档系统 FastAPI 主接口
提供文件上传、查询、管理、归档、作品库生成等API
"""
import os
import sys
import json
import uvicorn
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage import LocalObjectStorage
from database import MediaDatabase
from archiver import MediaArchiver
from gallery_gen import GalleryGenerator
from evolution import EvolutionEngine, get_evolution_engine

# 配置
CONFIG = {
    "storage_path": "/opt/storage/media",
    "db_path": "/opt/storage/media/media.db",
    "chain_path": "/opt/storage/media/archive_chain.json",
    "gallery_path": "/opt/storage/media/gallery",
    "api_token": "ZR-MEDIA-2026-OMEGA-d04bb54ba2a55a7d",
    "max_file_size": 500 * 1024 * 1024,  # 500MB
    "allowed_types": {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp',
                       '.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv',
                       '.mp3', '.wav', '.ogg', '.flac', '.m4a'}
}

# 初始化
app = FastAPI(title="火斗云智媒体归档系统", version="1.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局组件
storage = None
db = None
archiver = None
gallery_gen = None
evolution = None

def init_components():
    """初始化组件"""
    global storage, db, archiver, gallery_gen, evolution
    if storage is None:
        storage = LocalObjectStorage(CONFIG["storage_path"])
    if db is None:
        db = MediaDatabase(CONFIG["db_path"])
    if archiver is None:
        archiver = MediaArchiver(db, storage, CONFIG["chain_path"])
    if gallery_gen is None:
        gallery_gen = GalleryGenerator(db, CONFIG["gallery_path"])
    if evolution is None:
        evolution = get_evolution_engine(CONFIG["storage_path"] + "/evolution")

# 依赖注入
def get_storage():
    init_components()
    return storage

def get_db():
    init_components()
    return db

def get_archiver():
    init_components()
    return archiver

def get_gallery():
    init_components()
    return gallery_gen

def get_evolution():
    init_components()
    return evolution

def verify_token(token: str = Form(None)):
    """验证API Token"""
    if token != CONFIG["api_token"]:
        raise HTTPException(status_code=403, detail="无效的API Token")
    return True

# 模型
class FileInfoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    tags: Optional[List[str]] = None
    gallery_visible: Optional[int] = None

class ArchiveRequest(BaseModel):
    file_hash: str
    lock_level: int = 4

# 挂载静态文件（作品库和存储）
@app.on_event("startup")
async def startup_event():
    init_components()
    # 挂载作品库静态目录
    if os.path.exists(CONFIG["gallery_path"]):
        app.mount("/gallery", StaticFiles(directory=CONFIG["gallery_path"], html=True), name="gallery")
    # 挂载存储目录
    if os.path.exists(CONFIG["storage_path"]):
        app.mount("/media", StaticFiles(directory=CONFIG["storage_path"]), name="media")

# ========== API 接口 ==========

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "火斗云智媒体归档系统",
        "version": "1.0.0",
        "time": datetime.now().isoformat()
    }

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    token: str = Form(...),
    title: str = Form(None),
    description: str = Form(None),
    prompt: str = Form(None),
    tags: str = Form(None),
    source: str = Form("doubao"),
    _: bool = Depends(verify_token)
):
    """
    上传文件并自动归档
    支持图片、视频、音频
    """
    init_components()
    
    # 检查文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in CONFIG["allowed_types"]:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")
    
    # 读取文件内容
    content = await file.read()
    
    # 检查文件大小
    if len(content) > CONFIG["max_file_size"]:
        raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {CONFIG['max_file_size']//1024//1024}MB")
    
    # 保存到对象存储
    storage_path, file_type, file_hash = storage.save_bytes(
        content, file.filename
    )
    
    # 解析标签
    tag_list = []
    if tags:
        try:
            tag_list = json.loads(tags)
        except:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    
    # 保存到数据库
    file_id = db.add_file(
        file_hash=file_hash,
        filename=file.filename,
        storage_path=storage_path,
        file_type=file_type,
        file_size=len(content),
        title=title,
        description=description,
        prompt=prompt,
        tags=tag_list,
        source=source
    )
    
    # 自动归档（Lv4）
    archive_result = archiver.archive_file(file_hash, lock_level=4)
    
    # 重新生成作品库
    gallery_result = gallery_gen.regenerate_all()
    
    return {
        "success": True,
        "file_id": file_id,
        "file_hash": file_hash,
        "filename": file.filename,
        "file_type": file_type,
        "file_size": len(content),
        "storage_path": storage_path,
        "archive": archive_result,
        "gallery_regenerated": True,
        "gallery_url": "/gallery/index.html"
    }

@app.get("/api/files")
async def list_files(
    file_type: str = None,
    tag: str = None,
    limit: int = 50,
    offset: int = 0,
    db: MediaDatabase = Depends(get_db)
):
    """列出文件"""
    files = db.list_files(file_type=file_type, tag=tag, limit=limit, offset=offset)
    total = db.get_stats()['total_files']
    return {
        "files": files,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/files/{file_hash}")
async def get_file(file_hash: str, db: MediaDatabase = Depends(get_db)):
    """获取文件详情"""
    file_info = db.get_file_by_hash(file_hash)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    # 获取归档日志
    archive_logs = db.get_archive_logs(file_hash)
    file_info['archive_logs'] = archive_logs
    return file_info

@app.put("/api/files/{file_hash}")
async def update_file(
    file_hash: str,
    update: FileInfoUpdate,
    token: str = Form(...),
    db: MediaDatabase = Depends(get_db),
    _: bool = Depends(verify_token)
):
    """更新文件信息"""
    file_info = db.get_file_by_hash(file_hash)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    update_data = update.dict(exclude_unset=True)
    db.update_file_info(file_hash, **update_data)
    
    return {"success": True, "updated": update_data}

@app.delete("/api/files/{file_hash}")
async def delete_file(
    file_hash: str,
    token: str = Form(...),
    db: MediaDatabase = Depends(get_db),
    storage: LocalObjectStorage = Depends(get_storage),
    _: bool = Depends(verify_token)
):
    """删除文件"""
    # 删除存储文件
    storage.delete_file(file_hash)
    # 删除数据库记录
    db.delete_file(file_hash)
    return {"success": True, "file_hash": file_hash}

@app.post("/api/archive")
async def archive_file(
    request: ArchiveRequest,
    token: str = Form(...),
    archiver: MediaArchiver = Depends(get_archiver),
    _: bool = Depends(verify_token)
):
    """手动归档文件"""
    result = archiver.archive_file(request.file_hash, lock_level=request.lock_level)
    return result

@app.get("/api/archive/chain")
async def get_archive_chain(archiver: MediaArchiver = Depends(get_archiver)):
    """获取归档链信息"""
    return archiver.get_chain_info()

@app.get("/api/archive/verify")
async def verify_chain(archiver: MediaArchiver = Depends(get_archiver)):
    """验证归档链完整性"""
    return archiver.verify_chain_integrity()

@app.get("/api/stats")
async def get_stats(db: MediaDatabase = Depends(get_db)):
    """获取统计信息"""
    return db.get_stats()

@app.get("/api/tags")
async def get_tags(db: MediaDatabase = Depends(get_db)):
    """获取所有标签"""
    return db.get_all_tags()

@app.post("/api/gallery/regenerate")
async def regenerate_gallery(
    token: str = Form(...),
    gallery: GalleryGenerator = Depends(get_gallery),
    _: bool = Depends(verify_token)
):
    """重新生成作品库"""
    result = gallery.regenerate_all()
    return result

@app.get("/api/gallery")
async def get_gallery_info():
    """获取作品库信息"""
    return {
        "url": "/gallery/index.html",
        "description": "火斗云智AI作品库 - 豆包APP生成的图片视频自动归档展示"
    }

# ========== 进化引擎 API ==========

@app.get("/api/evolution/summary")
async def get_evolution_summary(evolution: EvolutionEngine = Depends(get_evolution)):
    """获取进化总结"""
    return evolution.get_evolution_summary()

@app.get("/api/evolution/roadmap")
async def get_evolution_roadmap(evolution: EvolutionEngine = Depends(get_evolution)):
    """获取进化路线图"""
    return evolution.get_evolution_roadmap()

@app.get("/api/evolution/logs")
async def get_evolution_logs(
    limit: int = 50,
    evolution: EvolutionEngine = Depends(get_evolution)
):
    """获取进化日志"""
    logs = evolution.logs[-limit:] if limit > 0 else evolution.logs
    return {
        "total": len(evolution.logs),
        "logs": logs[::-1]  # 最新的在前
    }

@app.post("/api/evolution/record")
async def record_evolution(
    evo_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    impact: str = Form("medium"),
    token: str = Form(...),
    evolution: EvolutionEngine = Depends(get_evolution),
    _: bool = Depends(verify_token)
):
    """记录一次进化"""
    log = evolution.record_evolution(
        evo_type=evo_type,
        title=title,
        description=description,
        impact=impact
    )
    return {
        "success": True,
        "log": log
    }

@app.post("/api/evolution/upgrade")
async def upgrade_version(
    major: int = Form(None),
    minor: int = Form(None),
    patch: int = Form(None),
    stage: str = Form(None),
    token: str = Form(...),
    evolution: EvolutionEngine = Depends(get_evolution),
    _: bool = Depends(verify_token)
):
    """版本升级"""
    new_version = evolution.upgrade_version(
        major=major,
        minor=minor,
        patch=patch,
        stage=stage
    )
    return {
        "success": True,
        "new_version": new_version,
        "current_stage": evolution.current_stage
    }

@app.post("/api/evolution/feedback")
async def add_evolution_feedback(
    feedback_type: str = Form(...),
    content: str = Form(...),
    rating: int = Form(0),
    evolution: EvolutionEngine = Depends(get_evolution)
):
    """添加用户反馈（驱动进化）"""
    feedback = evolution.add_feedback(
        feedback_type=feedback_type,
        content=content,
        rating=rating
    )
    return {
        "success": True,
        "feedback": feedback,
        "message": "感谢您的反馈！系统将根据反馈持续进化。"
    }

@app.get("/api/evolution/feedbacks")
async def get_evolution_feedbacks(
    status: str = None,
    limit: int = 50,
    evolution: EvolutionEngine = Depends(get_evolution)
):
    """获取反馈列表"""
    feedbacks = evolution.feedbacks
    if status:
        feedbacks = [f for f in feedbacks if f["status"] == status]
    return {
        "total": len(feedbacks),
        "feedbacks": feedbacks[-limit:][::-1]
    }

@app.post("/api/evolution/optimize")
async def trigger_optimization(
    token: str = Form(...),
    evolution: EvolutionEngine = Depends(get_evolution),
    _: bool = Depends(verify_token)
):
    """触发自动优化"""
    evolution._auto_optimize()
    return {
        "success": True,
        "message": "自动优化已触发",
        "optimization_count": evolution.metrics.optimization_count,
        "current_config": {
            "max_retries": evolution.config.get("max_retries", 3),
            "chunk_size": evolution.config.get("chunk_size", 8*1024*1024)
        }
    }

@app.get("/api/evolution/plugins")
async def get_evolution_plugins(evolution: EvolutionEngine = Depends(get_evolution)):
    """获取已注册的进化插件"""
    return {
        "total": len(evolution.plugins),
        "plugins": evolution.plugins
    }

# 主入口
if __name__ == "__main__":
    print("=" * 60)
    print("🔥 火斗云智媒体归档系统启动中...")
    print(f"存储路径: {CONFIG['storage_path']}")
    print(f"数据库: {CONFIG['db_path']}")
    print(f"作品库: {CONFIG['gallery_path']}")
    print(f"API Token: {CONFIG['api_token'][:20]}...")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9130,
        log_level="info"
    )
