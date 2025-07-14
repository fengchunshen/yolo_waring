from flask import Flask, render_template, Response, send_from_directory, request
from flask_socketio import SocketIO
from flask_cors import CORS
import cv2
import numpy as np
from intrusion_detector import IntrusionDetector
import json
import threading
import time
import queue
import os

app = Flask(__name__)

# 配置CORS，允许跨域请求（开发环境）
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# 配置SocketIO，允许跨域
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"], 
                   async_mode='threading', ping_timeout=10, ping_interval=5)

# 全局变量
detector = None
camera = None
is_running = False
rtsp_url = "rtsp://admin:fxt060919@192.168.0.123:554/cam/realmonitor?channel=1&subtype=0"

# 最新的帧
latest_frame = None
latest_processed_frame = None
frame_lock = threading.Lock()

def generate_frames(camera_index):
    global latest_processed_frame
    
    # 只有三楼机房一号位（camera_id=0）才返回真实视频流
    if camera_index != 0:
        # 其他摄像头返回占位符图像
        placeholder_frame = create_placeholder_frame(camera_index)
        ret, buffer = cv2.imencode('.jpg', placeholder_frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        return
    
    while is_running:
        # 检查 detector 是否已初始化
        if detector is None:
            time.sleep(0.1)
            continue
            
        with frame_lock:
            if latest_processed_frame is None:
                time.sleep(0.1)
                continue
            frame = latest_processed_frame.copy()
        
        # 将帧转换为JPEG格式
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def create_placeholder_frame(camera_index):
    """创建占位符图像"""
    # 创建黑色背景
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 摄像头位置映射
    locations = {
        0: '三楼机房1号点位', 1: '三楼机房2号点位', 2: '三楼机房3号点位',
        3: '四楼机房1号点位', 4: '四楼机房2号点位', 5: '四楼机房3号点位',
        6: '五楼机房1号点位', 7: '五楼机房2号点位', 8: '五楼机房3号点位'
    }
    
    location_name = locations.get(camera_index, f'摄像头{camera_index}')
    
    # 添加文字
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.2
    thickness = 2
    color = (255, 255, 255)  # 白色文字
    
    # 计算文字位置使其居中
    text_size = cv2.getTextSize(location_name, font, font_scale, thickness)[0]
    text_x = (frame.shape[1] - text_size[0]) // 2
    text_y = (frame.shape[0] + text_size[1]) // 2
    
    # 绘制文字
    cv2.putText(frame, location_name, (text_x, text_y), font, font_scale, color, thickness)
    
    # 添加"暂无视频流"提示
    status_text = "暂无视频流"
    status_font_scale = 0.8
    status_thickness = 1
    status_color = (128, 128, 128)  # 灰色文字
    
    status_text_size = cv2.getTextSize(status_text, font, status_font_scale, status_thickness)[0]
    status_text_x = (frame.shape[1] - status_text_size[0]) // 2
    status_text_y = text_y + 60
    
    cv2.putText(frame, status_text, (status_text_x, status_text_y), font, status_font_scale, status_thickness)
    
    return frame

# Vue前端路由（生产环境）
@app.route('/')
def index():
    # 如果存在Vue构建的文件，使用Vue版本
    if os.path.exists('dist/index.html'):
        return send_from_directory('dist', 'index.html')
    else:
        # 否则使用原始模板
        return render_template('index.html')

@app.route('/<path:path>')
def static_proxy(path):
    """为Vue构建的静态文件提供服务"""
    try:
        # 首先尝试从dist目录提供文件
        if os.path.exists('dist'):
            return send_from_directory('dist', path)
        else:
            # 回退到Flask的静态文件
            return send_from_directory('static', path)
    except Exception as e:
        print(f"静态文件服务错误: {e}")
        # 如果文件不存在，返回Vue的index.html（用于SPA路由）
        if os.path.exists('dist/index.html'):
            return send_from_directory('dist', 'index.html')
        else:
            return "文件未找到", 404

# 原始模板路由（向后兼容）
@app.route('/original')
def original_index():
    return render_template('index.html')

# 视频流端点
@app.route('/video_feed/<int:camera_id>')
def video_feed(camera_id):
    """视频流端点"""
    print(f"请求视频流: 摄像头 {camera_id}")
    return Response(generate_frames(camera_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# 系统状态API端点
@app.route('/api/system/status')
def system_status():
    """系统状态API"""
    return {
        'status': 'running' if is_running else 'stopped',
        'detector_initialized': detector is not None,
        'camera_connected': camera is not None,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }

# 摄像头列表API端点
@app.route('/api/cameras')
def cameras_list():
    """摄像头列表API"""
    cameras = [
        {'id': 0, 'name': '三楼机房1号点位', 'status': 'active'},
        {'id': 1, 'name': '三楼机房2号点位', 'status': 'inactive'},
        {'id': 2, 'name': '三楼机房3号点位', 'status': 'inactive'},
        {'id': 3, 'name': '四楼机房1号点位', 'status': 'inactive'},
        {'id': 4, 'name': '四楼机房2号点位', 'status': 'inactive'},
        {'id': 5, 'name': '四楼机房3号点位', 'status': 'inactive'},
        {'id': 6, 'name': '五楼机房1号点位', 'status': 'inactive'},
        {'id': 7, 'name': '五楼机房2号点位', 'status': 'inactive'},
        {'id': 8, 'name': '五楼机房3号点位', 'status': 'inactive'}
    ]
    return {'cameras': cameras}

# Socket.IO事件处理
@socketio.on('connect')
def handle_connect():
    print('客户端连接成功')
    # 发送系统状态信息
    socketio.emit('system_status', {
        'status': 'connected',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'message': '系统连接正常'
    })

@socketio.on('disconnect')
def handle_disconnect():
    print('客户端断开连接')

@socketio.on('ping')
def handle_ping():
    """处理客户端ping"""
    socketio.emit('pong')

def on_intrusion_event(event):
    """
    入侵事件回调函数，直接处理检测到的事件
    """
    try:
        # 确保事件数据格式正确
        event_data = {
            'timestamp': event['timestamp'],
            'confidence': float(event['confidence']) if event['confidence'] != -1.0 else 0.95,
            'position': [float(event['position'][0]), float(event['position'][1])],
            'camera_id': event.get('camera_id', 0),
            'person_id': event.get('person_id', 'unknown'),
            'time_since_first': event.get('time_since_first', 0)
        }
        
        # 立即发送事件到所有连接的客户端
        socketio.emit('intrusion_alert', event_data)
        print(f"实时发送告警信息: {event_data}")
        
        # 发送系统状态更新
        socketio.emit('system_status', {
            'status': 'alert_sent',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'检测到入侵事件，人员ID: {event_data["person_id"]}'
        })
        
    except Exception as e:
        print(f"处理入侵事件时出错: {str(e)}")

def start_detection():
    global detector, camera, is_running
    
    print("正在启动入侵检测系统...")
    
    # 初始化检测器
    detector = IntrusionDetector()
    print("检测器初始化完成")
    
    # 注册事件回调函数
    detector.add_event_callback(on_intrusion_event)
    print("事件回调函数已注册")
    
    # 打开RTSP视频流
    camera = cv2.VideoCapture(rtsp_url)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    print(f"RTSP视频流已连接: {rtsp_url}")
    
    is_running = True
    
    # 启动视频读取线程
    video_thread = threading.Thread(target=video_loop)
    video_thread.daemon = True
    video_thread.start()
    print("视频读取线程已启动")
    
    # 启动检测线程
    detection_thread = threading.Thread(target=detection_loop)
    detection_thread.daemon = True
    detection_thread.start()
    print("检测线程已启动")
    
    print("入侵检测系统启动完成，开始持续监控...")

def video_loop():
    global camera, is_running, latest_frame
    
    print("视频读取线程已启动，开始读取视频流...")
    frame_count = 0
    
    while is_running:
        # 检查 camera 是否已初始化
        if camera is None:
            time.sleep(0.1)
            continue
            
        success, frame = camera.read()
        if not success:
            print("无法读取视频流，尝试重新连接...")
            camera.release()
            time.sleep(1)  # 等待1秒后重试
            camera = cv2.VideoCapture(rtsp_url)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue
        
        with frame_lock:
            latest_frame = frame
        
        frame_count += 1
        if frame_count % 100 == 0:  # 每100帧打印一次状态
            print(f"视频读取线程运行中，已读取 {frame_count} 帧")

def detection_loop():
    """独立的检测线程，持续进行入侵检测"""
    global detector, latest_frame, latest_processed_frame, is_running
    
    print("检测线程已启动，开始持续检测...")
    frame_count = 0
    
    while is_running:
        # 检查 detector 是否已初始化
        if detector is None:
            time.sleep(0.1)
            continue
            
        with frame_lock:
            if latest_frame is None:
                time.sleep(0.1)
                continue
            frame = latest_frame.copy()
        
        # 进行入侵检测处理
        processed_frame = detector.process_frame(frame, camera_id=0)
        
        # 更新处理后的帧
        with frame_lock:
            latest_processed_frame = processed_frame
        
        frame_count += 1
        if frame_count % 100 == 0:  # 每100帧打印一次状态
            print(f"检测线程运行中，已处理 {frame_count} 帧")
        
        # 控制检测频率（每秒约10帧）
        time.sleep(0.1)

if __name__ == '__main__':
    # 检查是否需要安装flask-cors
    try:
        import flask_cors
    except ImportError:
        print("警告: flask-cors 未安装。如果需要跨域支持，请运行: pip install flask-cors")
    
    print("启动支持Vue前端的Flask应用...")
    print("Vue前端开发服务器: http://localhost:3000")
    print("Flask后端API服务器: http://localhost:5000")
    print("原始HTML版本: http://localhost:5000/original")
    
    start_detection()
    socketio.run(app, debug=True, use_reloader=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True) 