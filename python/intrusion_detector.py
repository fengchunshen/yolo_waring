import cv2
import numpy as np
import torch
from ultralytics import YOLO
import time
from datetime import datetime
import pandas as pd
from typing import List, Tuple, Dict, Callable
from collections import deque
from typing import Optional, Callable
class KalmanTracker:
    def __init__(self, initial_center: Tuple[int, int]):
        """
        为单个人员初始化卡尔曼滤波器
        状态向量: [x, y, vx, vy] - 位置和速度
        观测向量: [x, y] - 检测到的位置
        """
        self.kalman = cv2.KalmanFilter(4, 2)  # 4个状态变量，2个观测变量
        
        # 状态转移矩阵 (匀速直线运动模型)
        dt = 1.0  # 时间间隔，假设为1帧
        self.kalman.transitionMatrix = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
        # 观测矩阵 (只能观测到位置)
        self.kalman.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)
        
        # 过程噪声协方差矩阵
        self.kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.1
        
        # 观测噪声协方差矩阵
        self.kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1.0
        
        # 后验误差协方差矩阵
        self.kalman.errorCovPost = np.eye(4, dtype=np.float32) * 1.0
        
        # 初始状态 [x, y, vx, vy]
        x, y = initial_center
        self.kalman.statePre = np.array([x, y, 0, 0], dtype=np.float32)
        self.kalman.statePost = np.array([x, y, 0, 0], dtype=np.float32)
        
        self.age = 0  # 跟踪器年龄
        self.hits = 1  # 成功匹配次数
        self.hit_streak = 1  # 连续命中次数
        self.time_since_update = 0  # 自上次更新以来的时间
    
    def predict(self) -> Tuple[int, int]:
        """
        预测下一个位置
        :return: 预测的中心点坐标
        """
        predicted = self.kalman.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        
        return int(predicted[0]), int(predicted[1])
    
    def update(self, center: Tuple[int, int]):
        """
        用观测值更新卡尔曼滤波器
        :param center: 观测到的中心点坐标
        """
        measurement = np.array([center[0], center[1]], dtype=np.float32)
        self.kalman.correct(measurement)
        
        self.hits += 1
        self.hit_streak += 1
        self.time_since_update = 0
    
    def get_state(self) -> Tuple[int, int]:
        """
        获取当前状态的位置
        :return: 当前位置
        """
        state = self.kalman.statePost
        return int(state[0]), int(state[1])
    
    def get_velocity(self) -> Tuple[float, float]:
        """
        获取当前速度
        :return: 当前速度 (vx, vy)
        """
        state = self.kalman.statePost
        return float(state[2]), float(state[3])

class PersonTracker:
    def __init__(self, position_threshold: int = 100, max_disappeared: int = 10, min_hits: int = 1):
        """
        初始化基于卡尔曼滤波的人员追踪器
        :param position_threshold: 匹配同一人的最大像素距离
        :param max_disappeared: 一个ID在被删除前可以消失的最大帧数
        :param min_hits: 创建稳定跟踪所需的最小命中次数
        """
        self.trackers: Dict[str, Dict] = {}  # 存储所有跟踪器
        self.next_person_id = 0
        self.position_threshold = position_threshold
        self.max_disappeared = max_disappeared
        self.min_hits = min_hits

    def _get_center(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        x1, y1, x2, y2 = bbox
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    def _calculate_iou(self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """
        计算两个边界框的IoU (Intersection over Union)
        """
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # 计算交集
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

    def update(self, detections: np.ndarray) -> List[Dict]:
        """
        用当前帧的检测结果更新追踪状态 (使用卡尔曼滤波)
        :param detections: YOLO模型输出的检测结果 (x1, y1, x2, y2, conf, class_id)
        :return: 当前所有被追踪到的人员列表
        """
        # 第一步：所有跟踪器进行预测
        predicted_positions = {}
        for person_id, tracker_data in self.trackers.items():
            kalman_tracker = tracker_data['kalman']
            predicted_center = kalman_tracker.predict()
            predicted_positions[person_id] = predicted_center

        # 第二步：匹配检测与跟踪器
        current_detections = []
        for det in detections:
            x1, y1, x2, y2, conf, _ = det
            bbox = (int(x1), int(y1), int(x2), int(y2))
            center = self._get_center(bbox)
            current_detections.append({
                'bbox': bbox, 
                'center': center, 
                'confidence': float(conf),
                'matched': False
            })

        # 使用匈牙利算法进行最优匹配 (简化版本)
        matched_pairs = []
        unmatched_detections = []
        unmatched_trackers = list(self.trackers.keys())

        if len(current_detections) > 0 and len(self.trackers) > 0:
            # 计算距离矩阵
            cost_matrix = np.zeros((len(current_detections), len(self.trackers)))
            tracker_ids = list(self.trackers.keys())
            
            for i, det in enumerate(current_detections):
                for j, tracker_id in enumerate(tracker_ids):
                    predicted_center = predicted_positions[tracker_id]
                    distance = np.linalg.norm(np.array(det['center']) - np.array(predicted_center))
                    cost_matrix[i, j] = distance

            # 简化匹配：对每个检测找最近的跟踪器
            for i, det in enumerate(current_detections):
                min_cost = float('inf')
                best_tracker_idx = -1
                
                for j, tracker_id in enumerate(tracker_ids):
                    if tracker_id in unmatched_trackers and cost_matrix[i, j] < min_cost:
                        min_cost = cost_matrix[i, j]
                        best_tracker_idx = j
                
                if best_tracker_idx != -1 and min_cost < self.position_threshold:
                    matched_tracker_id = tracker_ids[best_tracker_idx]
                    matched_pairs.append((i, matched_tracker_id))
                    unmatched_trackers.remove(matched_tracker_id)
                    det['matched'] = True
                else:
                    unmatched_detections.append(i)
        else:
            # 如果没有现有跟踪器，所有检测都是未匹配的
            unmatched_detections = list(range(len(current_detections)))
        
        print(f"未匹配检测数量: {len(unmatched_detections)}")

        # 第三步：更新匹配的跟踪器
        for det_idx, tracker_id in matched_pairs:
            detection = current_detections[det_idx]
            tracker_data = self.trackers[tracker_id]
            kalman_tracker = tracker_data['kalman']
            
            # 用观测值更新卡尔曼滤波器
            kalman_tracker.update(detection['center'])
            
            # 更新跟踪器数据
            tracker_data['bbox'] = detection['bbox']
            tracker_data['center'] = kalman_tracker.get_state()
            tracker_data['confidence'] = detection['confidence']
            tracker_data['velocity'] = kalman_tracker.get_velocity()

        # 第四步：创建新的跟踪器
        print(f"准备创建 {len(unmatched_detections)} 个新跟踪器")
        for det_idx in unmatched_detections:
            detection = current_detections[det_idx]
            self.next_person_id += 1
            new_id = str(self.next_person_id)
            
            kalman_tracker = KalmanTracker(detection['center'])
            self.trackers[new_id] = {
                'id': new_id,
                'kalman': kalman_tracker,
                'bbox': detection['bbox'],
                'center': detection['center'],
                'confidence': detection['confidence'],
                'velocity': (0.0, 0.0)
            }
            print(f"创建新的卡尔曼跟踪器: ID={new_id}, 位置={detection['center']}")
        
        print(f"当前总跟踪器数量: {len(self.trackers)}")

        # 第五步：删除过期的跟踪器
        expired_ids = []
        for tracker_id in unmatched_trackers:
            kalman_tracker = self.trackers[tracker_id]['kalman']
            if kalman_tracker.time_since_update > self.max_disappeared:
                expired_ids.append(tracker_id)

        for tracker_id in expired_ids:
            print(f"删除过期的卡尔曼跟踪器: ID={tracker_id}")
            del self.trackers[tracker_id]

        # 第六步：返回稳定的跟踪结果
        valid_trackers = []
        for tracker_id, tracker_data in self.trackers.items():
            kalman_tracker = tracker_data['kalman']
            # 降低门槛：新创建的跟踪器（hits=1）或稳定的跟踪器都可以显示
            if kalman_tracker.hits >= 1 or kalman_tracker.time_since_update == 0:
                # 更新中心位置为卡尔曼滤波器的输出
                tracker_data['center'] = kalman_tracker.get_state()
                valid_trackers.append(tracker_data)

        print(f"有效跟踪器数量: {len(valid_trackers)} (总跟踪器: {len(self.trackers)})")
        return valid_trackers

class IntrusionDetector:
    def __init__(self, model_path: str = "yolov8n.pt"):
        """
        初始化入侵检测器 (优化版)
        :param model_path: YOLOv8模型路径
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"正在使用设备: {self.device}")
        self.model = YOLO(model_path)
        self.tracker = PersonTracker(position_threshold=100, max_disappeared=10, min_hits=1) # 使用新追踪器
        
        self.events = []  # 存储事件记录
        self.confidence_threshold = 0.5
        self.person_class_id = 0  # COCO数据集中人的类别ID
        
        # 报警逻辑相关状态
        self.person_timestamps: Dict[str, float] = {}  # 存储每个人的首次检测时间
        self.person_alert_times: Dict[str, float] = {} # 存储每个人的上次报警时间
        self.person_alert_levels: Dict[str, int] = {} # 存储每个人的报警等级
        
        self.alert_intervals = [10, 30, 60]  # 报警时间间隔（秒）
        self.current_camera_id = 0
        
        # 新增：事件回调函数
        self.event_callbacks: List[Callable] = []
        self.report_alert_callback: Optional[Callable] = None
        
        # 设备信息配置
        self.device_info = {
            'deviceId': 0,
            'deviceName': '默认摄像头',
            'facilityId': 1,
            'facilityName': '默认设施'
        }

        
    def add_event_callback(self, callback: Callable):
        """
        添加事件回调函数
        :param callback: 当检测到事件时调用的函数
        """
        if callback not in self.event_callbacks:
            self.event_callbacks.append(callback)

    def set_report_alert_callback(self, callback: Callable):
        """【新增】设置上报告警到RuoYi的回调函数"""
        self.report_alert_callback = callback

    def _trigger_event_callbacks(self, event: Dict):
        """
        触发所有事件回调函数
        :param event: 事件数据
        """
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"执行WebSocket事件回调时出错: {str(e)}")
    def _trigger_report_alert(self, event_data: Dict):
        """【新增】触发上报告警到RuoYi的回调函数"""
        if self.report_alert_callback:
            try:
                # 准备上报给RuoYi的数据
                report_data = {
                    "deviceId": event_data.get('deviceId'),
                    "facilityId": event_data.get('facilityId'),
                    "personId": event_data.get('person_id'),
                    "confidence": event_data.get('confidence'),
                    "position": event_data.get('position'),
                    "remark": f"在 {event_data.get('facilityName', '')} 的 {event_data.get('deviceName', '')} 检测到人员",
                    # "screenshotUrl": "..." # 可以在这里添加截图上传逻辑
                }
                self.report_alert_callback(report_data)
            except Exception as e:
                print(f"执行上报告警回调时出错: {str(e)}")
        else:
            print("警告: 未设置上报告警回调函数，无法上报。")


    def should_alert(self, person_id: str, current_time: float) -> bool:
        """
        判断是否应该触发报警 (更稳健的逻辑)
        :param person_id: 人员ID
        :param current_time: 当前时间
        :return: 是否应该报警
        """
        first_detection_time = self.person_timestamps.get(person_id)
        if first_detection_time is None:
            # 这种情况不应该发生，因为我们在检测到人后会立即记录时间
            return False

        time_since_first = current_time - first_detection_time
        current_alert_level = self.person_alert_levels.get(person_id, 0)
        
        # 立即报警：如果是首次检测到的人（当前报警等级为0），立即触发报警
        if current_alert_level == 0:
            self.person_alert_levels[person_id] = 1
            return True
        
        # 检查是否达到下一个报警时间点
        next_alert_level = current_alert_level + 1
        
        # 检查预设的10, 30, 60秒报警点
        if next_alert_level <= len(self.alert_intervals):
            threshold_time = self.alert_intervals[next_alert_level - 1]
            if time_since_first >= threshold_time:
                self.person_alert_levels[person_id] = next_alert_level
                return True
        # 检查超过60秒后的周期性报警
        elif time_since_first > self.alert_intervals[-1]:
            last_alert_time = self.person_alert_times.get(person_id, first_detection_time)
            # 每60秒报警一次
            if current_time - last_alert_time >= 60:
                self.person_alert_levels[person_id] = next_alert_level
                return True
                
        return False

    def process_frame(self, frame: np.ndarray, camera_id: int = 0) -> np.ndarray:
        """
        处理单帧图像 (对外接口不变)
        :param frame: 输入帧
        :param camera_id: 摄像头ID
        :return: 处理后的帧
        """
        self.current_camera_id = camera_id
        results = self.model(frame, device=self.device, conf=self.confidence_threshold, classes=[self.person_class_id], verbose=False)
        
        detections = results[0].boxes.data.cpu().numpy()
        current_time = time.time()
        
        # 添加调试信息
        print(f"原始检测数量: {len(detections)}")
        
        # 使用卡尔曼滤波追踪器更新人员状态
        tracked_persons = self.tracker.update(detections)
        
        print(f"跟踪器数量: {len(tracked_persons)}")
        
        for person in tracked_persons:
            person_id = person['id']
            bbox = person['bbox']
            center = person['center']
            confidence = person.get('confidence', 0.0)
            velocity = person.get('velocity', (0.0, 0.0))
            
            # 如果是新追踪到的人，记录其首次出现时间
            if person_id not in self.person_timestamps:
                self.person_timestamps[person_id] = current_time
                print(f"检测到新人: ID={person_id}, 位置=({center[0]}, {center[1]}), 速度=({velocity[0]:.1f}, {velocity[1]:.1f})")

            # 检查是否需要报警
            if self.should_alert(person_id, current_time):
                # 记录事件 (包含更多信息)
                event = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'confidence': confidence,
                    'position': [center[0], center[1]],
                    'velocity': [velocity[0], velocity[1]],
                    'person_id': person_id,
                    'time_since_first': current_time - self.person_timestamps[person_id],
                    # 【新增】将设备和设施信息加入事件
                    'deviceId': camera_id,
                    'deviceName': self.device_info.get('deviceName', '未知设备'),
                    'facilityId': self.device_info.get('facilityId'),
                    'facilityName': self.device_info.get('facilityName', '未知设施')
                }
                self.events.append(event)
                self.person_alert_times[person_id] = current_time # 更新该ID的最后报警时间
                self._trigger_event_callbacks(event)
                self._trigger_report_alert(event)
                print(f"触发告警: {event}")
                
                # 立即触发事件回调
                self._trigger_event_callbacks(event)
            
            # 在图像上绘制边界框和详细信息
            x1, y1, x2, y2 = bbox
            
            # 根据跟踪状态选择颜色
            kalman_tracker = self.tracker.trackers[person_id]['kalman']
            if kalman_tracker.time_since_update == 0:
                # 当前帧有检测：绿色
                color = (0, 255, 0)
                status = "ACTIVE"
            else:
                # 预测状态：黄色
                color = (0, 255, 255)
                status = "PREDICTED"
            
            # 绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # 绘制中心点
            cv2.circle(frame, center, 3, color, -1)
            
            # 绘制速度向量（放大显示）
            vx, vy = velocity
            if abs(vx) > 0.1 or abs(vy) > 0.1:
                end_point = (int(center[0] + vx * 10), int(center[1] + vy * 10))
                cv2.arrowedLine(frame, center, end_point, (255, 0, 255), 2, tipLength=0.3)
            
            # 显示详细信息
            info_lines = [
                f"ID:{person_id}",
                f"Conf:{confidence:.2f}" if confidence > 0 else f"Hits:{kalman_tracker.hits}"
            ]
            
            # 绘制信息背景
            info_height = len(info_lines) * 15 + 5
            cv2.rectangle(frame, (x1, y1 - info_height - 5), (x1 + 100, y1), (0, 0, 0), -1)
            cv2.rectangle(frame, (x1, y1 - info_height - 5), (x1 + 100, y1), color, 1)
            
            # 绘制信息文本
            for i, line in enumerate(info_lines):
                cv2.putText(frame, line, (x1 + 3, y1 - info_height + i * 15 + 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # 在帧上显示统计信息
        stats_text = [
            f"Trackers: {len(tracked_persons)}",
            f"Camera: {camera_id}"
        ]
        
        for i, text in enumerate(stats_text):
            cv2.putText(frame, text, (10, 25 + i * 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, text, (10, 25 + i * 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        return frame

    def save_events(self, filename: str = "intrusion_events.csv"):
        """
        保存事件记录到CSV文件 (对外接口不变)
        """
        if self.events:
            df = pd.DataFrame(self.events)
            df.to_csv(filename, index=False, encoding='utf-8-sig')

def main():
    # 初始化检测器
    detector = IntrusionDetector()
    
    # 打开RTSP视频流
    rtsp_url = "rtsp://admin:fxt060919@192.168.0.123:554/cam/realmonitor?channel=1&subtype=0"
    cap = cv2.VideoCapture(rtsp_url)
    
    # 设置缓冲区大小
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("无法读取视频流，尝试重新连接...")
                cap.release()
                time.sleep(1)
                cap = cv2.VideoCapture(rtsp_url)
                continue

            processed_frame = detector.process_frame(frame)
            cv2.imshow('Intrusion Detection', processed_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.save_events()

if __name__ == "__main__":
    main()