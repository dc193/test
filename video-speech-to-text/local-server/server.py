#!/usr/bin/env python3
"""
本地 Whisper 语音转文字服务
使用方法：
1. pip install flask flask-cors openai-whisper
2. python server.py
3. 打开浏览器访问 http://localhost:8000
"""

import os
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import whisper

app = Flask(__name__, static_folder='.')
CORS(app)

# 全局模型变量
model = None
model_name = "small"  # 可选: tiny, base, small, medium, large

def get_model():
    global model
    if model is None:
        print(f"正在加载 Whisper {model_name} 模型...")
        model = whisper.load_model(model_name)
        print("模型加载完成！")
    return model

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': '没有音频文件'}), 400

    audio_file = request.files['audio']
    language = request.form.get('language', 'zh')

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # 转录
        model = get_model()
        result = model.transcribe(
            tmp_path,
            language=language,
            task='transcribe'
        )

        return jsonify({
            'success': True,
            'text': result['text']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'ready': model is not None,
        'model': model_name
    })

if __name__ == '__main__':
    print("=" * 50)
    print("视频语音转文字服务")
    print("=" * 50)
    print(f"模型: {model_name}")
    print("访问: http://localhost:8000")
    print("=" * 50)

    # 预加载模型
    get_model()

    app.run(host='0.0.0.0', port=8000, debug=False)
