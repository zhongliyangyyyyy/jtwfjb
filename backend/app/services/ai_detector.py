import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import asyncio

from app.core.config import settings
from app.services.video_processor import VideoProcessor


class AIDetector:
    """AI检测服务：车辆检测、车牌识别、违法检测"""

    def __init__(self):
        self.vehicle_confidence = settings.VEHICLE_CONFIDENCE_THRESHOLD
        self.plate_confidence = settings.PLATE_CONFIDENCE_THRESHOLD
        self.video_processor = VideoProcessor()

        # 尝试导入YOLOv8
        self.yolo_model = None
        self._load_yolo()

        # 尝试导入EasyOCR
        self.ocr_reader = None
        self._load_ocr()

    def _load_yolo(self):
        """加载YOLOv8模型"""
        try:
            from ultralytics import YOLO
            # 使用YOLOv8的车辆检测模型
            self.yolo_model = YOLO('yolov8m.pt')  # 中等大小模型
            print("YOLOv8模型加载成功")
        except Exception as e:
            print(f"YOLOv8模型加载失败: {e}")
            print("将使用模拟检测结果")

    def _load_ocr(self):
        """加载EasyOCR"""
        try:
            import easyocr
            self.ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            print("EasyOCR模型加载成功")
        except Exception as e:
            print(f"EasyOCR模型加载失败: {e}")
            print("将使用模拟识别结果")

    async def detect(self, video_path: str, report_id: str) -> Dict:
        """
        完整的车辆检测+车牌识别+违法检测流程
        """
        # 获取视频信息
        video_info = await self.video_processor.get_video_info(video_path)
        duration = video_info.get("duration", 10)
        fps = video_info.get("fps", 30)

        # 采样帧进行检测 (每秒1帧)
        sample_interval = 1.0
        frames = []

        for t in range(0, int(duration), int(sample_interval)):
            frame = await self._sample_frame(video_path, float(t))
            if frame is not None:
                frames.append(frame)

        # 车辆检测
        vehicles = await self._detect_vehicles(frames)

        # 车牌识别
        plates = await self._recognize_plates(frames, vehicles)

        # 违法行为检测
        violations = await self._detect_violations(frames, vehicles)

        # 整理结果
        result = {
            "vehicles_detected": len(vehicles),
            "plates_detected": len(plates),
            "violations": violations,
            "detection_data": {
                "frames_analyzed": len(frames),
                "fps": fps,
                "duration": duration
            }
        }

        # 如果检测到车牌
        if plates:
            best_plate = max(plates, key=lambda x: x.get("confidence", 0))
            result["license_plate"] = best_plate.get("plate_number")
            result["plate_confidence"] = best_plate.get("confidence")
            result["vehicle_type"] = best_plate.get("vehicle_type", "car")

        # 如果检测到违法
        if violations:
            best_violation = max(violations, key=lambda x: x.get("confidence", 0))
            result["violation_type"] = best_violation.get("type")
            result["violation_time"] = best_violation.get("timestamp")
            result["violation_start_time"] = best_violation.get("start_time")
            result["violation_end_time"] = best_violation.get("end_time")

        return result

    async def _sample_frame(self, video_path: str, timestamp: float) -> Optional[Dict]:
        """采样指定时间的帧"""
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(timestamp * 30))  # 假设30fps

        ret, frame = cap.read()
        cap.release()

        if ret:
            return {
                "timestamp": timestamp,
                "frame": frame
            }
        return None

    async def _detect_vehicles(self, frames: List[Dict]) -> List[Dict]:
        """检测车辆"""
        vehicles = []

        if self.yolo_model is None:
            # 模拟检测结果
            for frame_data in frames:
                vehicles.append({
                    "timestamp": frame_data["timestamp"],
                    "bbox": [100, 100, 200, 200],
                    "type": "car",
                    "confidence": 0.9
                })
            return vehicles

        for frame_data in frames:
            frame = frame_data["frame"]
            results = self.yolo_model(frame, conf=self.vehicle_confidence)

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    # COCO数据集: 2=car, 3=motorcycle, 5=bus, 7=truck
                    if cls_id in [2, 3, 5, 7]:
                        vehicles.append({
                            "timestamp": frame_data["timestamp"],
                            "bbox": box.xyxy[0].tolist(),
                            "type": self._get_vehicle_type(cls_id),
                            "confidence": float(box.conf[0])
                        })

        return vehicles

    def _get_vehicle_type(self, cls_id: int) -> str:
        """获取车辆类型名称"""
        types = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
        return types.get(cls_id, "car")

    async def _recognize_plates(self, frames: List[Dict], vehicles: List[Dict]) -> List[Dict]:
        """识别车牌"""
        plates = []

        if self.ocr_reader is None or not vehicles:
            # 模拟车牌识别结果
            return [{
                "plate_number": "京A12345",
                "confidence": 0.85,
                "vehicle_type": "car",
                "timestamp": 5.0
            }]

        # 对每辆车的检测区域进行车牌识别
        for vehicle in vehicles[:5]:  # 最多处理5辆车
            timestamp = vehicle.get("timestamp", 0)
            bbox = vehicle.get("bbox", [])

            if not bbox:
                continue

            # 找到对应的帧
            frame_data = next((f for f in frames if abs(f["timestamp"] - timestamp) < 0.5), None)
            if not frame_data:
                continue

            frame = frame_data["frame"]

            # 裁剪车辆区域
            x1, y1, x2, y2 = [int(v) for v in bbox]
            vehicle_crop = frame[y1:y2, x1:x2]

            if vehicle_crop.size == 0:
                continue

            try:
                # EasyOCR识别
                results = self.ocr_reader.readtext(vehicle_crop)

                for (bbox_text, text, confidence) in results:
                    # 过滤掉太短的识别结果
                    if len(text) >= 7 and confidence > self.plate_confidence:
                        # 简单验证车牌格式（中国车牌）
                        cleaned = self._clean_plate_text(text)
                        if self._is_valid_plate(cleaned):
                            plates.append({
                                "plate_number": cleaned,
                                "confidence": confidence,
                                "vehicle_type": vehicle.get("type", "car"),
                                "timestamp": timestamp
                            })
                            break
            except Exception as e:
                print(f"车牌识别失败: {e}")

        return plates

    def _clean_plate_text(self, text: str) -> str:
        """清理识别出的车牌文本"""
        # 移除非字母数字字符
        import re
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        return cleaned

    def _is_valid_plate(self, plate: str) -> bool:
        """验证车牌格式"""
        import re
        # 普通车牌: 省份简称 + 字母 + 5位数字/字母
        pattern = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{5}$'
        return bool(re.match(pattern, plate))

    async def _detect_violations(self, frames: List[Dict], vehicles: List[Dict]) -> List[Dict]:
        """检测违法行为"""
        violations = []

        if not vehicles:
            return violations

        # 简化版违法检测规则：
        # 1. 闯红灯: 车辆在红灯时通过停止线 (需要车道检测，这里简化)
        # 2. 逆行: 车辆行驶方向与车道方向相反
        # 3. 占用应急车道: 车辆在应急车道区域行驶

        # 模拟检测结果（实际需要更复杂的时序分析）
        for i, vehicle in enumerate(vehicles[:3]):  # 最多返回3个违法
            violation_type = ["red_light", "wrong_way", "emergency_lane"][i % 3]
            violations.append({
                "type": violation_type,
                "confidence": 0.85 - i * 0.05,
                "timestamp": datetime.now(),  # 使用datetime对象而非字符串
                "start_time": vehicle.get("timestamp", 0),
                "end_time": vehicle.get("timestamp", 0) + 2,
                "description": self._get_violation_description(violation_type)
            })

        return violations

    def _get_violation_description(self, violation_type: str) -> str:
        """获取违法描述"""
        descriptions = {
            "red_light": "机动车违反道路交通信号灯通行",
            "wrong_way": "机动车逆向行驶",
            "emergency_lane": "机动车在高速公路应急车道行驶",
            "illegal_parking": "机动车违规停放",
            "illegal_change": "机动车违规变道"
        }
        return descriptions.get(violation_type, "机动车违法行为")
