import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Optional
import json

from app.core.config import settings


class VideoProcessor:
    """视频处理服务，使用FFmpeg"""

    def __init__(self):
        self.ffmpeg_path = "ffmpeg"  # 系统FFmpeg
        self.ffprobe_path = "ffprobe"

    async def get_video_info(self, video_path: str) -> Dict:
        """获取视频信息"""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            info = json.loads(result.stdout)

            video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)

            return {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size": int(info.get("format", {}).get("size", 0)),
                "width": int(video_stream.get("width", 0)) if video_stream else 0,
                "height": int(video_stream.get("height", 0)) if video_stream else 0,
                "fps": self._parse_fps(video_stream.get("r_frame_rate", "0/1")) if video_stream else 0,
            }
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return {"duration": 0, "size": 0, "width": 0, "height": 0, "fps": 0}

    def _parse_fps(self, fps_str: str) -> float:
        """解析帧率字符串"""
        try:
            num, denom = fps_str.split("/")
            return float(num) / float(denom)
        except:
            return 0

    async def process(self, video_path: str, report_id: str) -> Dict:
        """处理视频：转码、生成缩略图等"""
        # 获取视频信息
        info = await self.get_video_info(video_path)
        return info

    async def generate_thumbnail(self, video_path: str, report_id: str, timestamp: float = 1) -> str:
        """生成视频缩略图"""
        output_path = settings.THUMBNAILS_DIR / f"{report_id}.jpg"

        cmd = [
            self.ffmpeg_path,
            "-y",  # 覆盖输出
            "-ss", str(timestamp),  # 跳到指定时间
            "-i", video_path,
            "-vframes", "1",  # 只取一帧
            "-q:v", "2",  # 质量
            "-vf", "scale=640:-1",  # 缩放宽度
            str(output_path)
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
            return str(output_path)
        except Exception as e:
            print(f"生成缩略图失败: {e}")
            return ""

    async def extract_clip(
        self,
        video_path: str,
        report_id: str,
        start_time: float,
        end_time: float
    ) -> Dict:
        """提取视频片段"""
        # 确保时间有效
        start_time = max(0, start_time)
        duration = max(1, end_time - start_time)

        output_path = settings.CLIPS_DIR / f"{report_id}.mp4"

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-c", "copy",  # 直接复制流，不重新编码
            "-avoid_negative_ts", "make_zero",
            str(output_path)
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=300)
            return {
                "clip_path": str(output_path),
                "start_time": start_time,
                "end_time": end_time
            }
        except Exception as e:
            print(f"提取视频片段失败: {e}")
            return {"clip_path": "", "start_time": start_time, "end_time": end_time}

    async def extract_frames(
        self,
        video_path: str,
        report_id: str,
        interval: float = 1.0
    ) -> list:
        """按间隔提取帧"""
        frames_dir = settings.FRAMES_DIR / report_id
        frames_dir.mkdir(parents=True, exist_ok=True)

        info = await self.get_video_info(video_path)
        duration = info.get("duration", 0)
        fps = info.get("fps", 30)

        frames = []
        current_time = 0.0

        while current_time < duration:
            output_path = frames_dir / f"frame_{len(frames):04d}.jpg"

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-ss", str(current_time),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                str(output_path)
            ]

            try:
                subprocess.run(cmd, capture_output=True, timeout=30)
                if output_path.exists():
                    frames.append({
                        "path": str(output_path),
                        "timestamp": current_time
                    })
            except Exception as e:
                print(f"提取帧失败 at {current_time}: {e}")

            current_time += interval

        return frames
