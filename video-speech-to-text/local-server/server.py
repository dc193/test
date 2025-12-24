#!/usr/bin/env python3
"""
本地 Whisper 语音转文字服务（支持 Apple Silicon GPU 加速）
使用方法：
1. pip install flask flask-cors openai-whisper
2. python server.py
3. 打开浏览器访问 http://localhost:8000
"""

import os
import tempfile
import threading
import torch
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import whisper

app = Flask(__name__, static_folder='.')
CORS(app)

# 全局变量
model = None
model_name = "medium"  # 可选: tiny, base, small, medium, large
device = None

# 转录进度
progress_info = {
    'status': 'idle',  # idle, loading, transcribing, done, error
    'progress': 0,
    'message': ''
}

def get_device():
    """检测并返回最佳设备"""
    global device
    if device is not None:
        return device

    if torch.backends.mps.is_available():
        device = "mps"
        print("✓ 检测到 Apple Silicon GPU，使用 MPS 加速")
    elif torch.cuda.is_available():
        device = "cuda"
        print("✓ 检测到 NVIDIA GPU，使用 CUDA 加速")
    else:
        device = "cpu"
        print("✗ 未检测到 GPU，使用 CPU（较慢）")

    return device

def get_model():
    global model, progress_info
    if model is None:
        progress_info['status'] = 'loading'
        progress_info['message'] = f'正在加载 Whisper {model_name} 模型...'
        print(f"正在加载 Whisper {model_name} 模型到 {get_device()}...")

        # 加载模型到指定设备
        model = whisper.load_model(model_name, device=get_device())

        print("模型加载完成！")
        progress_info['status'] = 'idle'
        progress_info['message'] = '模型已加载'
    return model

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    global progress_info

    # 支持 'audio' 或 'file' 字段
    audio_file = request.files.get('audio') or request.files.get('file')
    if not audio_file:
        return jsonify({'error': '没有音频文件'}), 400

    language = request.form.get('language', 'zh')

    # 获取文件扩展名
    filename = audio_file.filename or 'audio.webm'
    ext = os.path.splitext(filename)[1] or '.webm'

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        progress_info['status'] = 'transcribing'
        progress_info['progress'] = 0
        progress_info['message'] = '正在转录...'

        # 获取音频时长（用于估算进度）
        import subprocess
        try:
            result_duration = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', tmp_path],
                capture_output=True, text=True
            )
            total_duration = float(result_duration.stdout.strip())
            progress_info['message'] = f'正在转录... (音频时长: {int(total_duration//60)}分{int(total_duration%60)}秒)'
        except:
            total_duration = 0

        # 转录（使用 verbose=True 可以看到进度）
        model = get_model()
        result = model.transcribe(
            tmp_path,
            language=language,
            task='transcribe',
            verbose=True,  # 在终端显示进度
            fp16=(get_device() != "cpu")  # GPU 用 FP16，CPU 用 FP32
        )

        progress_info['status'] = 'done'
        progress_info['progress'] = 100
        progress_info['message'] = '转录完成'

        return jsonify({
            'success': True,
            'text': result['text']
        })
    except Exception as e:
        progress_info['status'] = 'error'
        progress_info['message'] = str(e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.route('/progress', methods=['GET'])
def get_progress():
    """获取当前转录进度"""
    return jsonify(progress_info)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'ready': model is not None,
        'model': model_name,
        'device': device or 'unknown'
    })

if __name__ == '__main__':
    print("=" * 50)
    print("视频语音转文字服务")
    print("=" * 50)
    print(f"模型: {model_name}")
    print(f"设备: {get_device()}")
    print("访问: http://localhost:8000")
    print("=" * 50)

    # 预加载模型
    get_model()

    app.run(host='0.0.0.0', port=8000, debug=False)
