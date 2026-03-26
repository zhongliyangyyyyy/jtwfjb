import os
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db, AsyncSessionLocal
from app.models.report import Report
from app.services.video_processor import VideoProcessor
from app.services.ai_detector import AIDetector
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["举报"])


@router.get("")
async def list_reports(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取举报列表"""
    query = select(Report).order_by(Report.created_at.desc())

    if status:
        query = query.where(Report.status == status)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()

    return {
        "total": len(reports),
        "reports": [r.to_dict() for r in reports]
    }


@router.get("/{report_id}")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """获取举报详情"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    return report.to_dict()


@router.post("/{report_id}/analyze")
async def analyze_report(
    report_id: str,
    db: AsyncSession = Depends(get_db)
):
    """触发AI分析（同步执行）"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    if report.status not in ["pending", "failed"]:
        raise HTTPException(status_code=400, detail=f"当前状态不允许分析: {report.status}")

    # 更新状态
    report.status = "processing"
    await db.commit()

    try:
        # 1. 视频预处理
        video_processor = VideoProcessor()
        video_info = await video_processor.process(str(report.video_path), report_id)
        report.video_duration = video_info.get("duration")

        # 生成缩略图
        thumbnail_path = await video_processor.generate_thumbnail(
            str(report.video_path),
            report_id
        )
        report.thumbnail_path = thumbnail_path

        # 2. AI检测
        ai_detector = AIDetector()
        detection_result = await ai_detector.detect(
            str(report.video_path),
            report_id
        )

        # 更新检测结果
        report.license_plate = detection_result.get("license_plate")
        report.plate_confidence = detection_result.get("plate_confidence")
        report.vehicle_type = detection_result.get("vehicle_type")
        report.violation_type = detection_result.get("violation_type")
        report.violation_time = detection_result.get("violation_time")
        report.detection_data = detection_result.get("detection_data")

        # 提取违法片段
        if detection_result.get("violation_start_time"):
            clip_info = await video_processor.extract_clip(
                str(report.video_path),
                report_id,
                detection_result["violation_start_time"] - 3,
                detection_result["violation_end_time"] + 3
            )
            report.clip_path = clip_info.get("clip_path")
            report.clip_start_time = clip_info.get("start_time")
            report.clip_end_time = clip_info.get("end_time")

        report.status = "completed"

    except Exception as e:
        report.status = "failed"
        report.error_message = str(e)

    await db.commit()

    return {"message": "分析完成", "report_id": report_id, "status": report.status}


@router.get("/{report_id}/download")
async def download_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """下载举报报告（PDF）"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    if report.status != "completed":
        raise HTTPException(status_code=400, detail="分析未完成，无法生成报告")

    # 生成PDF
    generator = ReportGenerator()
    pdf_path = await generator.generate(report)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"举报报告_{report.license_plate or report.id}.pdf"
    )


@router.get("/{report_id}/video")
async def get_video(report_id: str, db: AsyncSession = Depends(get_db)):
    """获取视频文件"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    if not os.path.exists(report.video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    return FileResponse(
        report.video_path,
        media_type="video/mp4",
        filename=report.video_filename
    )


@router.get("/{report_id}/clip")
async def get_video_clip(report_id: str, db: AsyncSession = Depends(get_db)):
    """获取违法视频片段"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    if not report.clip_path or not os.path.exists(report.clip_path):
        raise HTTPException(status_code=404, detail="视频片段不存在")

    return FileResponse(
        report.clip_path,
        media_type="video/mp4",
        filename=f"违法片段_{report.license_plate or report_id}.mp4"
    )


@router.delete("/{report_id}")
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """删除举报记录"""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    # 删除文件
    for path_attr in ["video_path", "thumbnail_path", "clip_path"]:
        file_path = getattr(report, path_attr)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

    await db.delete(report)
    await db.commit()

    return {"message": "删除成功"}
