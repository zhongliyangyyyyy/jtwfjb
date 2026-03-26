from sqlalchemy import Column, String, Float, DateTime, Text, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import JSON
from app.core.database import Base
import uuid


class Report(Base):
    """举报记录模型"""
    __tablename__ = "violation_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 视频信息
    video_filename = Column(String(255), nullable=False)
    video_path = Column(String(500), nullable=False)
    video_duration = Column(Float, nullable=True)  # 秒
    video_size = Column(Integer, nullable=True)  # 字节
    thumbnail_path = Column(String(500), nullable=True)

    # 车牌信息
    license_plate = Column(String(20), nullable=True)
    plate_confidence = Column(Float, nullable=True)
    vehicle_type = Column(String(30), nullable=True)  # 轿车、货车、客车

    # 违法信息
    violation_type = Column(String(50), nullable=True)  # red_light, wrong_way, emergency_lane
    violation_time = Column(DateTime, nullable=True)
    violation_location = Column(String(500), nullable=True)  # 地址描述
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)

    # 证据片段
    clip_path = Column(String(500), nullable=True)
    clip_start_time = Column(Float, nullable=True)
    clip_end_time = Column(Float, nullable=True)

    # 检测结果详情 (JSON格式存储)
    detection_data = Column(JSON, nullable=True)

    # 状态: pending, processing, completed, failed
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "video_filename": self.video_filename,
            "video_duration": self.video_duration,
            "video_size": self.video_size,
            "thumbnail_path": self.thumbnail_path,
            "license_plate": self.license_plate,
            "plate_confidence": self.plate_confidence,
            "vehicle_type": self.vehicle_type,
            "violation_type": self.violation_type,
            "violation_time": self.violation_time.isoformat() if self.violation_time else None,
            "violation_location": self.violation_location,
            "gps_latitude": self.gps_latitude,
            "gps_longitude": self.gps_longitude,
            "clip_path": self.clip_path,
            "clip_start_time": self.clip_start_time,
            "clip_end_time": self.clip_end_time,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
