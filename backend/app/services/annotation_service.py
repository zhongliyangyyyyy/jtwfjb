"""
违规标注服务
在图像上绘制检测结果标注
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from app.core.config import settings


class AnnotationService:
    """违规标注服务"""

    # 违规类型对应的颜色 (BGR格式)
    VIOLATION_COLORS = {
        "red_light": (0, 0, 255),       # 红色 - 闯红灯
        "wrong_way": (255, 0, 255),      # 紫红色 - 逆行
        "emergency_lane": (0, 255, 255), # 黄色 - 占用应急车道
        "solid_line_change": (255, 165, 0), # 橙色 - 跨实线变道
        "illegal_change": (255, 165, 0),   # 橙色 - 违规变道
        "illegal_parking": (128, 0, 128),  # 紫色 - 违规停车
    }

    # 车道线颜色
    LANE_COLORS = {
        "solid": (0, 200, 0),    # 绿色实线
        "dashed": (0, 255, 0),   # 亮绿色虚线
        "stop": (0, 0, 255)      # 红色停止线
    }

    def __init__(self):
        self.violations_dir = settings.VIOLATIONS_DIR
        self.violations_dir.mkdir(parents=True, exist_ok=True)

    def annotate_frame(
        self,
        frame: np.ndarray,
        violation_type: str,
        vehicle_bbox: List[float],
        lane_lines: Optional[List[Dict]] = None,
        stop_line: Optional[Dict] = None,
        traffic_light_state: Optional[str] = None
    ) -> np.ndarray:
        """
        在帧上绘制违规标注

        Args:
            frame: 原始图像
            violation_type: 违规类型
            vehicle_bbox: 车辆边界框 [x1, y1, x2, y2]
            lane_lines: 车道线列表
            stop_line: 停止线信息
            traffic_light_state: 交通灯状态

        Returns:
            标注后的图像
        """
        annotated = frame.copy()

        # 获取违规颜色
        violation_color = self.VIOLATION_COLORS.get(
            violation_type,
            (0, 0, 255)  # 默认红色
        )

        # 绘制车道线
        if lane_lines:
            self._draw_lane_lines(annotated, lane_lines)

        # 绘制停止线
        if stop_line:
            self._draw_stop_line(annotated, stop_line)

        # 绘制交通灯状态
        if traffic_light_state:
            self._draw_traffic_light_indicator(annotated, traffic_light_state)

        # 绘制车辆边界框
        if vehicle_bbox and len(vehicle_bbox) == 4:
            self._draw_vehicle_bbox(annotated, vehicle_bbox, violation_type, violation_color)

        # 绘制违规标签
        if vehicle_bbox and len(vehicle_bbox) == 4:
            self._draw_violation_label(annotated, vehicle_bbox, violation_type, violation_color)

        return annotated

    def _draw_lane_lines(self, frame: np.ndarray, lane_lines: List[Dict]):
        """绘制车道线"""
        for line in lane_lines:
            start = tuple(int(x) for x in line["start"])
            end = tuple(int(x) for x in line["end"])

            # 实线用绿色，虚线用亮绿
            if line.get("length", 0) > 100:
                color = self.LANE_COLORS["solid"]
                thickness = 3
            else:
                color = self.LANE_COLORS["dashed"]
                thickness = 2

            cv2.line(frame, start, end, color, thickness)

    def _draw_stop_line(self, frame: np.ndarray, stop_line: Dict):
        """绘制停止线"""
        start = tuple(int(x) for x in stop_line["start"])
        end = tuple(int(x) for x in stop_line["end"])
        cv2.line(frame, start, end, self.LANE_COLORS["stop"], 4)

    def _draw_vehicle_bbox(
        self,
        frame: np.ndarray,
        bbox: List[float],
        violation_type: str,
        color: tuple
    ):
        """绘制车辆边界框"""
        x1, y1, x2, y2 = [int(v) for v in bbox]

        # 绘制矩形边框
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

        # 填充透明度区域
        overlay = frame.copy()
        cv2.fillPoly(overlay, [np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])], color)
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

        # 重新绘制边框（覆盖混合区域）
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

    def _draw_violation_label(
        self,
        frame: np.ndarray,
        bbox: List[float],
        violation_type: str,
        color: tuple
    ):
        """绘制违规标签"""
        x1, y1 = int(bbox[0]), int(bbox[1])

        # 违规描述
        descriptions = {
            "red_light": "RED LIGHT",
            "wrong_way": "WRONG WAY",
            "emergency_lane": "EMERGENCY LANE",
            "solid_line_change": "SOLID LINE CHANGE",
            "illegal_change": "ILLEGAL LANE CHANGE",
            "illegal_parking": "ILLEGAL PARKING"
        }

        label = descriptions.get(violation_type, violation_type.upper())

        # 绘制标签背景
        (label_w, label_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2
        )

        cv2.rectangle(
            frame,
            (x1, y1 - label_h - 15),
            (x1 + label_w + 10, y1),
            color,
            -1
        )

        # 绘制标签文字
        cv2.putText(
            frame,
            label,
            (x1 + 5, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

    def _draw_traffic_light_indicator(self, frame: np.ndarray, state: str):
        """绘制交通灯状态指示"""
        height, width = frame.shape[:2]

        # 在右上角绘制交通灯图标
        center_x = width - 80
        center_y = 80

        # 背景圆
        cv2.circle(frame, (center_x, center_y), 30, (50, 50, 50), -1)

        # 根据状态绘制颜色
        colors = {
            "red": (0, 0, 255),
            "yellow": (0, 255, 255),
            "green": (0, 255, 0)
        }

        if state in colors:
            cv2.circle(frame, (center_x, center_y), 20, colors[state], -1)

            # 绘制文字
            state_text = {"red": "红灯", "yellow": "黄灯", "green": "绿灯"}[state]
            cv2.putText(
                frame,
                state_text,
                (center_x - 25, center_y + 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                colors.get(state, (255, 255, 255)),
                2
            )

    def save_violation_image(
        self,
        annotated_frame: np.ndarray,
        report_id: str,
        violation_type: str
    ) -> str:
        """
        保存标注图像

        Args:
            annotated_frame: 标注后的图像
            report_id: 报告ID
            violation_type: 违规类型

        Returns:
            保存的文件路径
        """
        # 创建报告专属目录
        report_dir = self.violations_dir / report_id
        report_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        filename = f"{violation_type}_annotated.jpg"
        output_path = report_dir / filename

        # 保存图像
        cv2.imwrite(str(output_path), annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

        return str(output_path)

    def get_violation_image_path(self, report_id: str, violation_type: str) -> Optional[str]:
        """获取违规标注图像路径"""
        report_dir = self.violations_dir / report_id
        filename = f"{violation_type}_annotated.jpg"
        image_path = report_dir / filename

        if image_path.exists():
            return str(image_path)
        return None
