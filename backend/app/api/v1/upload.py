import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.models.report import Report

router = APIRouter(prefix="/upload", tags=["上传"])

# 存储上传会话信息
upload_sessions = {}


@router.post("/init")
async def init_upload(
    filename: str = Form(...),
    file_size: int = Form(...),
    total_chunks: int = Form(...)
):
    """初始化上传会话"""
    upload_id = str(uuid.uuid4())
    upload_sessions[upload_id] = {
        "filename": filename,
        "file_size": file_size,
        "total_chunks": total_chunks,
        "uploaded_chunks": [],
        "created_at": datetime.now()
    }

    # 创建临时目录
    temp_dir = settings.UPLOAD_DIR / upload_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    return {
        "upload_id": upload_id,
        "chunk_size": settings.CHUNK_SIZE,
        "total_chunks": total_chunks
    }


@router.post("/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...)
):
    """上传单个分片"""
    if upload_id not in upload_sessions:
        raise HTTPException(status_code=400, detail="无效的上传会话")

    session = upload_sessions[upload_id]

    # 保存分片
    chunk_path = settings.UPLOAD_DIR / upload_id / f"chunk_{chunk_index}"
    with open(chunk_path, "wb") as f:
        content = await chunk.read()
        f.write(content)

    session["uploaded_chunks"].append(chunk_index)

    uploaded_size = len(session["uploaded_chunks"]) * settings.CHUNK_SIZE
    progress = min(100, int(uploaded_size / session["file_size"] * 100))

    return {
        "chunk_index": chunk_index,
        "progress": progress,
        "uploaded_chunks": len(session["uploaded_chunks"]),
        "total_chunks": session["total_chunks"]
    }


@router.post("/complete")
async def complete_upload(
    upload_id: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    """完成上传，合并分片"""
    if upload_id not in upload_sessions:
        raise HTTPException(status_code=400, detail="无效的上传会话")

    session = upload_sessions[upload_id]

    if len(session["uploaded_chunks"]) != session["total_chunks"]:
        raise HTTPException(
            status_code=400,
            detail=f"分片不完整: 已上传 {len(session['uploaded_chunks'])}, 需 {session['total_chunks']}"
        )

    # 合并文件
    final_filename = f"{upload_id}_{session['filename']}"
    final_path = settings.UPLOAD_DIR / final_filename

    with open(final_path, "wb") as outfile:
        for i in range(session["total_chunks"]):
            chunk_path = settings.UPLOAD_DIR / upload_id / f"chunk_{i}"
            with open(chunk_path, "rb") as infile:
                outfile.write(infile.read())
            # 删除已合并的分片
            os.remove(chunk_path)

    # 清理会话
    os.rmdir(settings.UPLOAD_DIR / upload_id)
    del upload_sessions[upload_id]

    # 创建数据库记录
    async with AsyncSessionLocal() as db:
        report = Report(
            id=str(uuid.uuid4()),
            video_filename=session["filename"],
            video_path=str(final_path),
            video_size=session["file_size"],
            status="pending"
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

    return {
        "report_id": report.id,
        "video_path": str(final_path),
        "video_size": session["file_size"]
    }


@router.post("/simple")
async def simple_upload(
    file: UploadFile = File(...),
    violation_location: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    """简单上传（直接上传整个文件，适合小文件）"""
    # 生成唯一ID
    report_id = str(uuid.uuid4())

    # 保存文件
    file_extension = Path(file.filename).suffix
    saved_filename = f"{report_id}{file_extension}"
    file_path = settings.UPLOAD_DIR / saved_filename

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 创建数据库记录
    async with AsyncSessionLocal() as db:
        report = Report(
            id=report_id,
            video_filename=file.filename,
            video_path=str(file_path),
            video_size=len(content),
            violation_location=violation_location,
            status="pending"
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

    return {
        "report_id": report_id,
        "message": "上传成功"
    }
