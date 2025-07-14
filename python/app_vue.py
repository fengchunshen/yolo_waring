# python/app_vue.py

import cv2
import json
import numpy as np
import os
import queue
import requests
import threading
import time

from flask import Flask, Response, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from intrusion_detector import IntrusionDetector

# --- 1. 全局配置 ---
RUOYI_BASE_URL = "http://192.168.0.189:8080"
RUOYI_DEVICE_LIST_URL = f"{RUOYI_BASE_URL}/api/yolo/device/list"
RUOYI_AUTH_URL = f"{RUOYI_BASE_URL}/api/auth/token"
APP_KEY = "yolo-client"
APP_SECRET = "pFztYpMTYXQBmAUZRTaZ"

USE_HTTPS = RUOYI_BASE_URL.startswith('https://')
VERIFY_SSL = True

# --- 2. 全局变量 ---
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"])
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

detector = None
is_running = False
devices_info = {}
latest_processed_frames = {}
frame_lock = threading.Lock()

def load_rtsp_mapping():
    """从配置文件加载RTSP地址映射"""
    try:
        with open('rtsp_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            mapping = {}
            for device_id, device_config in config.get('rtsp_mapping', {}).items():
                mapping[device_id] = device_config['rtsp_url']
            return mapping
    except:
        return {
            '3': 'rtsp://admin:admin123@192.168.1.100:554/stream1',
            '4': 'rtsp://admin:admin123@192.168.1.101:554/stream1',
        }

RTSP_URL_MAPPING = load_rtsp_mapping()
auth_token = None
token_expire_time = 0

# --- 3. 认证与数据获取 ---
def get_ruoyi_auth_token():
    """获取或刷新RuoYi的认证Token"""
    global auth_token, token_expire_time

    if auth_token and token_expire_time > time.time() + 300:
        return auth_token

    payload = {"appKey": APP_KEY, "appSecret": APP_SECRET}
    verify_param = VERIFY_SSL if USE_HTTPS else False
    
    try:
        response = requests.post(RUOYI_AUTH_URL, json=payload, timeout=5, verify=verify_param)
        if response.status_code == 200 and response.json().get('code') == 200:
            auth_token = response.json().get('data')
            token_expire_time = time.time() + (720 - 10) * 60
            return auth_token
    except Exception as e:
        print(f"获取Token失败: {e}")
    return None

def load_devices_from_ruoyi():
    """从RuoYi后端加载设备信息"""
    global devices_info
    token = get_ruoyi_auth_token()
    if not token:
        devices_info = {}
        return

    headers = {"Authorization": f"Bearer {token}"}
    verify_param = VERIFY_SSL if USE_HTTPS else False
    
    try:
        response = requests.get(RUOYI_DEVICE_LIST_URL, headers=headers, timeout=10, verify=verify_param)
        if response.status_code == 200 and response.json().get('code') == 200:
            devices_list = response.json().get('data', [])
            devices_info = {str(device['deviceId']): device for device in devices_list}
            
            for device_id, device_data in devices_info.items():
                rtsp_url = device_data.get('url', '') or device_data.get('rtspUrl', '')
                
                if not rtsp_url and str(device_id) in RTSP_URL_MAPPING:
                    device_data['rtspUrl'] = RTSP_URL_MAPPING[str(device_id)]
                elif rtsp_url:
                    device_data['rtspUrl'] = rtsp_url
                
                # 确保facilityName字段存在
                if 'facilityName' not in device_data:
                    device_data['facilityName'] = None
    except Exception as e:
        print(f"加载设备失败: {e}")

# --- 4. 核心视频处理逻辑 ---
def process_single_device(device_id, device_info):
    """处理单个设备的视频流"""
    global latest_processed_frames, detector
    rtsp_url = device_info.get('rtspUrl')
    if not rtsp_url:
        return

    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while is_running:
        if not cap.isOpened():
            time.sleep(5)
            cap.release()
            cap = cv2.VideoCapture(rtsp_url)
            continue

        success, frame = cap.read()
        if not success:
            time.sleep(0.5)
            continue

        try:
            if detector is None:
                time.sleep(0.1)
                continue
            processed_frame = detector.process_frame(frame, device_id)
            with frame_lock:
                latest_processed_frames[device_id] = processed_frame
        except Exception as e:
            print(f"处理帧错误: {e}")

        time.sleep(0.04)

    cap.release()

def on_intrusion_event(event):
    """入侵事件回调函数"""
    try:
        socketio.emit('intrusion_alert', event)
    except Exception as e:
        print(f"发送通知失败: {e}")

# --- 5. Flask & SocketIO 路由 ---
@app.route('/')
def index():
    return "YOLO AI-Warning-Service is running."

@app.route('/health')
def health_check():
    return {'status': 'ok', 'message': 'Service is running', 'timestamp': time.time()}

@app.route('/api/devices')
def get_devices():
    """提供设备列表，按facilityName分组"""
    if not devices_info:
        return {'code': 200, 'data': {}, 'message': 'success'}
    
    # 按facilityName分组
    grouped_devices = {}
    
    for device_id, device_info in devices_info.items():
        rtsp_url = device_info.get('rtspUrl', '')
        if not rtsp_url and str(device_id) in RTSP_URL_MAPPING:
            rtsp_url = RTSP_URL_MAPPING[str(device_id)]
        
        # 获取facilityName，如果为空则归为"未分配摄像头"
        facility_name = device_info.get('facilityName')
        if not facility_name:
            facility_name = "未分配摄像头"
        
        # 如果该分组不存在，则创建
        if facility_name not in grouped_devices:
            grouped_devices[facility_name] = []
        
        device_data = {
            'id': int(device_id),
            'name': device_info.get('deviceName', f'设备{device_id}'),
            'rtspUrl': rtsp_url,
            'status': 'active' if device_id in latest_processed_frames else 'inactive',
            'ip': device_info.get('ip', ''),
            'type': device_info.get('type', ''),
            'userName': device_info.get('userName', ''),
            'facilityName': facility_name
        }
        
        grouped_devices[facility_name].append(device_data)
    
    return {'code': 200, 'data': grouped_devices, 'message': 'success'}

@app.route('/api/devices/refresh', methods=['POST'])
def refresh_devices():
    """手动刷新设备列表"""
    try:
        global devices_info
        load_devices_from_ruoyi()
        
        # 重新启动视频处理线程
        for device_id, device_data in devices_info.items():
            # 检查是否已经有该设备的处理线程在运行
            if device_id not in latest_processed_frames:
                thread = threading.Thread(target=process_single_device, args=(device_id, device_data))
                thread.daemon = True
                thread.start()
        
        return {'code': 200, 'message': '设备列表刷新成功', 'data': {'device_count': len(devices_info)}}
    except Exception as e:
        return {'code': 500, 'message': f'刷新设备列表失败: {str(e)}', 'data': None}

@app.route('/api/devices/<int:device_id>/status')
def get_device_status(device_id):
    """获取单个设备状态"""
    if not devices_info:
        return {'code': 404, 'message': '设备信息未加载', 'data': None}
    
    device_info = devices_info.get(str(device_id))
    if not device_info:
        return {'code': 404, 'message': f'设备 {device_id} 不存在', 'data': None}
    
    # 检查设备是否在线，使用字符串类型的设备ID
    is_online = str(device_id) in latest_processed_frames
    
    # 获取设备状态信息
    status_info = {
        'deviceId': device_id,
        'deviceName': device_info.get('deviceName', f'设备{device_id}'),
        'status': 'online' if is_online else 'offline',
        'lastUpdate': time.time(),
        'rtspUrl': device_info.get('rtspUrl', ''),
        'isProcessing': is_online,
        'frameCount': len(latest_processed_frames) if is_online else 0
    }
    
    return {'code': 200, 'data': status_info, 'message': 'success'}

@app.route('/video_feed/<int:camera_id>')
def video_feed(camera_id):
    """提供实时视频流"""
    def generate():
        while True:
            with frame_lock:
                # 确保使用字符串类型的设备ID来查找帧
                frame = latest_processed_frames.get(str(camera_id))
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.04)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    socketio.emit('system_status', {'message': 'AI服务连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    pass

# --- 6. 主程序入口 ---
def start_detection_service():
    """启动AI检测服务"""
    global detector, is_running

    print("启动AI告警服务")
    is_running = True

    load_devices_from_ruoyi()
    if not devices_info:
        print("未加载到设备信息")

    detector = IntrusionDetector(model_path="yolov8n.pt")
    detector.add_event_callback(on_intrusion_event)
    detector.set_report_alert_callback(report_alert_to_ruoyi)

    for device_id, device_data in devices_info.items():
        thread = threading.Thread(target=process_single_device, args=(device_id, device_data))
        thread.daemon = True
        thread.start()

def report_alert_to_ruoyi(alert_data):
    """上报告警到RuoYi"""
    token = get_ruoyi_auth_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    report_url = f"{RUOYI_BASE_URL}/api/yolo/alert/report"
    verify_param = VERIFY_SSL if USE_HTTPS else False
    
    try:
        response = requests.post(report_url, json=alert_data, headers=headers, timeout=10, verify=verify_param)
        if response.status_code == 200 and response.json().get('code') == 200:
            print(f"告警上报成功: {alert_data.get('deviceId')}")
    except Exception as e:
        print(f"上报告警失败: {e}")

if __name__ == '__main__':
    start_detection_service()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)