"""
车道线检测服务
使用 OpenCV Hough 变换检测车道线、实线/虚线分类、停止线检测
"""
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple


class LaneDetector:
    """车道线检测服务"""

    def __init__(self):
        # 车道线颜色范围 (HSV)
        self.white_lower = np.array([0, 0, 200])
        self.white_upper = np.array([180, 30, 255])
        self.yellow_lower = np.array([20, 100, 100])
        self.yellow_upper = np.array([30, 255, 255])

        # Hough 变换参数
        self.rho = 2
        self.theta = np.pi / 180
        self.threshold = 50
        self.min_line_length = 30
        self.max_line_gap = 100

    def detect_lanes(self, frame: np.ndarray) -> Dict:
        """
        检测车道线

        Returns:
            {
                "lane_lines": [...],  # 所有检测到的线段
                "solid_lines": [...], # 实线
                "dashed_lines": [...], # 虚线
                "stop_line": {...},   # 停止线
                "horizontal_lines": [...] # 水平线（可能是停止线）
            }
        """
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)

        # 车道线区域（图像下半部分）
        height, width = frame.shape[:2]
        mask = np.zeros_like(edges)
        polygon = np.array([[
            (0, height),
            (width // 3, height // 2),
            (2 * width // 3, height // 2),
            (width, height)
        ]], dtype=np.int32)
        cv2.fillPoly(mask, polygon, 255)
        masked_edges = cv2.bitwise_and(edges, mask)

        # Hough 直线检测
        lines = cv2.HoughLinesP(
            masked_edges,
            self.rho,
            self.theta,
            self.threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap
        )

        result = {
            "lane_lines": [],
            "solid_lines": [],
            "dashed_lines": [],
            "stop_line": None,
            "horizontal_lines": []
        }

        if lines is None:
            return result

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # 计算线段长度和角度
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

            line_info = {
                "start": (x1, y1),
                "end": (x2, y2),
                "length": length,
                "angle": angle
            }

            result["lane_lines"].append(line_info)

            # 分类实线 vs 虚线
            # 虚线：角度接近水平（接近0或180度）且长度较短
            # 实线：角度接近水平且长度较长，或者几乎垂直
            if angle < 20 or angle > 160:
                # 水平线 - 可能是虚线车道线或停止线
                if length > 100:
                    result["solid_lines"].append(line_info)
                else:
                    result["dashed_lines"].append(line_info)
            elif 70 < angle < 110:
                # 垂直线 - 可能是车道边界
                result["solid_lines"].append(line_info)

        # 检测停止线（粗的水平线在下半部分）
        result["stop_line"] = self._detect_stop_line(lines)

        return result

    def _detect_stop_line(self, lines: Optional[np.ndarray]) -> Optional[Dict]:
        """检测停止线 - 粗的短水平线"""
        if lines is None:
            return None

        stop_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

            # 停止线特征：接近水平、较短、比较粗
            if angle < 15 or angle > 165:
                length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                # 停止线通常在图像下方，长度适中
                if 30 < length < 200 and y1 > 300:
                    stop_lines.append({
                        "start": (x1, y1),
                        "end": (x2, y2),
                        "length": length
                    })

        if stop_lines:
            # 返回最下方的那条（最可能是停止线）
            return max(stop_lines, key=lambda l: l["start"][1])
        return None

    def detect_solid_line_crossing(
        self,
        vehicle_bbox: List[float],
        lane_lines: List[Dict],
        prev_lane: Optional[int],
        curr_lane: int
    ) -> bool:
        """
        检测车辆是否跨越实线

        Args:
            vehicle_bbox: [x1, y1, x2, y2]
            lane_lines: 检测到的车道线
            prev_lane: 之前所在车道 (-1表示新车辆)
            curr_lane: 当前所在车道

        Returns:
            是否跨越实线
        """
        if prev_lane == -1 or prev_lane == curr_lane:
            return False

        # 获取车辆中心点
        x_center = (vehicle_bbox[0] + vehicle_bbox[2]) / 2

        # 检查跨越点是否有实线
        for line in lane_lines:
            if line in [l for l in lane_lines if self._is_solid_line(l)]:
                # 实线存在，且车辆从一条车道移动到另一条
                return True

        return False

    def _is_solid_line(self, line: Dict) -> bool:
        """判断是否为实线"""
        # 实线通常是长的连续线
        return line.get("length", 0) > 100

    def get_lane_position(self, x: float, lane_lines: List[Dict]) -> int:
        """
        根据x坐标判断车辆所在车道

        Returns:
            车道编号（从左到右0, 1, 2, ...）
        """
        if not lane_lines:
            return 0

        # 按x坐标排序车道线
        sorted_lines = sorted(lane_lines, key=lambda l: (l["start"][0] + l["end"][0]) / 2)

        # 简单分段
        lanes = []
        for line in sorted_lines:
            mid_x = (line["start"][0] + line["end"][0]) / 2
            lanes.append(mid_x)

        # 判断x落在哪个区间
        lane_idx = 0
        for i, lane_x in enumerate(lanes):
            if x < lane_x:
                break
            lane_idx = i + 1

        return lane_idx
