"""
车辆跟踪服务
跨帧跟踪车辆，检测变道行为
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TrackedVehicle:
    """跟踪的车辆"""
    vehicle_id: int
    bbox: List[float]  # [x1, y1, x2, y2]
    timestamp: float
    lane: int = 0
    center_x: float = 0
    center_y: float = 0
    history: List[Dict] = field(default_factory=list)  # 位置历史

    def update(self, bbox: List[float], timestamp: float, lane: int):
        """更新车辆位置"""
        self.bbox = bbox
        self.timestamp = timestamp
        self.lane = lane
        self.center_x = (bbox[0] + bbox[2]) / 2
        self.center_y = (bbox[1] + bbox[3]) / 2

        # 记录历史
        self.history.append({
            "lane": lane,
            "center_x": self.center_x,
            "timestamp": timestamp
        })

        # 保持历史长度
        if len(self.history) > 30:
            self.history.pop(0)


class VehicleTracker:
    """车辆跟踪服务"""

    def __init__(self, iou_threshold: float = 0.3):
        """
        Args:
            iou_threshold: IOU阈值，用于匹配车辆
        """
        self.iou_threshold = iou_threshold
        self.tracked_vehicles: Dict[int, TrackedVehicle] = {}
        self.next_vehicle_id = 0

    def update(self, vehicles: List[Dict], frame_idx: int, lane_detector=None) -> List[TrackedVehicle]:
        """
        更新跟踪

        Args:
            vehicles: 当前帧检测到的车辆列表
            frame_idx: 帧索引
            lane_detector: 车道线检测器（用于确定车道）

        Returns:
            当前帧跟踪的车辆列表
        """
        if not vehicles:
            return list(self.tracked_vehicles.values())

        # 计算当前检测到的车辆中心点
        current_centers = []
        for v in vehicles:
            bbox = v.get("bbox", [])
            if len(bbox) == 4:
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                current_centers.append((cx, cy, bbox, v.get("timestamp", 0)))
            else:
                current_centers.append((0, 0, bbox, v.get("timestamp", 0)))

        # 匹配已有跟踪的车辆
        matched_ids = set()
        matched_centers = []

        for vehicle_id, tracked in self.tracked_vehicles.items():
            best_match_idx = -1
            best_dist = float('inf')

            for i, (cx, cy, bbox, ts) in enumerate(current_centers):
                if i in matched_centers:
                    continue

                # 计算距离
                dist = np.sqrt((cx - tracked.center_x) ** 2 + (cy - tracked.center_y) ** 2)

                if dist < best_dist and dist < 150:  # 距离阈值
                    best_dist = dist
                    best_match_idx = i

            if best_match_idx >= 0:
                cx, cy, bbox, ts = current_centers[best_match_idx]
                # 确定车道
                lane = tracked.lane
                if lane_detector:
                    lane = lane_detector.get_lane_position(cx, [])

                tracked.update(bbox, ts, lane)
                matched_ids.add(vehicle_id)
                matched_centers.append(best_match_idx)

        # 处理未匹配的新车辆
        for i, (cx, cy, bbox, ts) in enumerate(current_centers):
            if i not in matched_centers:
                lane = 0
                if lane_detector:
                    lane = lane_detector.get_lane_position(cx, [])

                new_vehicle = TrackedVehicle(
                    vehicle_id=self.next_vehicle_id,
                    bbox=bbox,
                    timestamp=ts,
                    lane=lane,
                    center_x=cx,
                    center_y=cy
                )
                self.tracked_vehicles[self.next_vehicle_id] = new_vehicle
                self.next_vehicle_id += 1

        # 清理消失的车辆（超过一定帧没更新）
        to_remove = []
        for vid, tracked in self.tracked_vehicles.items():
            if frame_idx - tracked.timestamp > 5:  # 5帧没更新则移除
                to_remove.append(vid)

        for vid in to_remove:
            del self.tracked_vehicles[vid]

        return list(self.tracked_vehicles.values())

    def detect_lane_change(self, vehicle_id: int) -> bool:
        """
        检测车辆是否变道

        Args:
            vehicle_id: 车辆ID

        Returns:
            是否发生了变道
        """
        if vehicle_id not in self.tracked_vehicles:
            return False

        tracked = self.tracked_vehicles[vehicle_id]
        history = tracked.history

        if len(history) < 3:
            return False

        # 检查车道是否变化
        lanes = [h["lane"] for h in history[-5:]]  # 最近5帧

        # 如果有连续帧车道不同
        for i in range(len(lanes) - 1):
            if lanes[i] != lanes[i + 1]:
                return True

        return False

    def detect_solid_line_crossing(self, vehicle_id: int) -> bool:
        """检测车辆是否跨越实线"""
        if vehicle_id not in self.tracked_vehicles:
            return False

        tracked = self.tracked_vehicles[vehicle_id]
        history = tracked.history

        if len(history) < 5:
            return False

        # 检测车道突变
        lanes = [h["lane"] for h in history[-5:]]

        # 检查是否有明显车道变化
        unique_lanes = set(lanes)
        if len(unique_lanes) > 1:
            # 检查是否在相邻帧之间有变化
            for i in range(len(lanes) - 1):
                if abs(lanes[i] - lanes[i + 1]) >= 1:
                    return True

        return False

    def get_vehicle_history(self, vehicle_id: int) -> List[Dict]:
        """获取车辆历史轨迹"""
        if vehicle_id not in self.tracked_vehicles:
            return []
        return self.tracked_vehicles[vehicle_id].history
