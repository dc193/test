"""Web应用 - 提供与CEO对话的界面"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
from pathlib import Path

from ..roles.ceo import CEO


app = FastAPI(title="AI Company", version="0.1.0")

# 全局CEO实例（v0.1简单处理，后续改为session管理）
ceo_instance: CEO = None


def get_ceo() -> CEO:
    global ceo_instance
    if ceo_instance is None:
        ceo_instance = CEO()
    return ceo_instance


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    html_content = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Company v0.1</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #16213e;
            padding: 1rem 2rem;
            border-bottom: 1px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 1.5rem;
            color: #e94560;
        }
        .status {
            font-size: 0.9rem;
            color: #888;
        }
        .status .state {
            color: #4ecca3;
            font-weight: bold;
        }
        .chat-container {
            flex: 1;
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding-bottom: 1rem;
        }
        .message {
            margin-bottom: 1.5rem;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message .role {
            font-size: 0.85rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .message.user .role {
            color: #4ecca3;
        }
        .message.assistant .role {
            color: #e94560;
        }
        .message .content {
            background: #16213e;
            padding: 1rem 1.25rem;
            border-radius: 12px;
            line-height: 1.6;
            white-space: pre-wrap;
        }
        .message.user .content {
            background: #0f3460;
            border-left: 3px solid #4ecca3;
        }
        .message.assistant .content {
            border-left: 3px solid #e94560;
        }
        .input-area {
            display: flex;
            gap: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #0f3460;
        }
        .input-area textarea {
            flex: 1;
            padding: 1rem;
            border: none;
            border-radius: 12px;
            background: #16213e;
            color: #eee;
            font-size: 1rem;
            resize: none;
            min-height: 60px;
            max-height: 150px;
        }
        .input-area textarea:focus {
            outline: 2px solid #e94560;
        }
        .input-area button {
            padding: 1rem 2rem;
            border: none;
            border-radius: 12px;
            background: #e94560;
            color: white;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
        }
        .input-area button:hover {
            background: #ff6b6b;
        }
        .input-area button:disabled {
            background: #555;
            cursor: not-allowed;
        }
        .actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }
        .actions button {
            padding: 0.5rem 1rem;
            border: 1px solid #0f3460;
            border-radius: 8px;
            background: transparent;
            color: #888;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .actions button:hover {
            border-color: #e94560;
            color: #e94560;
        }
        .typing {
            display: inline-block;
            width: 20px;
        }
        .typing::after {
            content: '...';
            animation: typing 1s infinite;
        }
        @keyframes typing {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Company v0.1</h1>
        <div class="status">
            状态: <span class="state" id="state">等待中</span>
        </div>
    </div>

    <div class="chat-container">
        <div class="messages" id="messages">
            <div class="message assistant">
                <div class="role">CEO</div>
                <div class="content">你好！我是这家AI公司的CEO。

告诉我你想做什么，我会帮你把想法变成可执行的计划。

你有什么想法？</div>
            </div>
        </div>

        <div class="input-area">
            <textarea id="input" placeholder="输入你的想法..." rows="2"></textarea>
            <button id="send" onclick="sendMessage()">发送</button>
        </div>

        <div class="actions">
            <button onclick="resetChat()">重新开始</button>
        </div>
    </div>

    <script>
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('input');
        const sendBtn = document.getElementById('send');
        const stateEl = document.getElementById('state');

        // Enter发送
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        async function sendMessage() {
            const message = inputEl.value.trim();
            if (!message) return;

            // 禁用输入
            inputEl.disabled = true;
            sendBtn.disabled = true;

            // 显示用户消息
            addMessage('user', message);
            inputEl.value = '';

            // 显示typing indicator
            const assistantMsg = addMessage('assistant', '<span class="typing"></span>', true);

            try {
                // 调用API（流式）
                const response = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullContent = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    fullContent += chunk;
                    assistantMsg.querySelector('.content').textContent = fullContent;
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                }

                // 更新状态
                updateState();

            } catch (error) {
                assistantMsg.querySelector('.content').textContent = '出错了: ' + error.message;
            }

            // 恢复输入
            inputEl.disabled = false;
            sendBtn.disabled = false;
            inputEl.focus();
        }

        function addMessage(role, content, isHtml = false) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            div.innerHTML = `
                <div class="role">${role === 'user' ? '你' : 'CEO'}</div>
                <div class="content">${isHtml ? content : escapeHtml(content)}</div>
            `;
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            return div;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function updateState() {
            try {
                const response = await fetch('/api/state');
                const data = await response.json();
                const stateMap = {
                    'idle': '等待中',
                    'exploring': '需求探索中',
                    'planning': '计划制定中',
                    'executing': '执行中',
                    'reviewing': '验收中'
                };
                stateEl.textContent = stateMap[data.state] || data.state;
            } catch (e) {
                console.error(e);
            }
        }

        async function resetChat() {
            if (!confirm('确定要重新开始吗？')) return;

            await fetch('/api/reset', { method: 'POST' });

            messagesEl.innerHTML = `
                <div class="message assistant">
                    <div class="role">CEO</div>
                    <div class="content">你好！我是这家AI公司的CEO。

告诉我你想做什么，我会帮你把想法变成可执行的计划。

你有什么想法？</div>
                </div>
            `;

            updateState();
        }

        // 初始化
        updateState();
        inputEl.focus();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """普通对话"""
    ceo = get_ceo()
    response = await ceo.chat(request.message)
    return {"response": response, "state": ceo.get_state()}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话"""
    ceo = get_ceo()

    async def generate():
        async for chunk in ceo.stream_chat(request.message):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")


@app.get("/api/state")
async def get_state():
    """获取当前状态"""
    ceo = get_ceo()
    return ceo.get_state()


@app.post("/api/reset")
async def reset():
    """重置对话"""
    ceo = get_ceo()
    ceo.reset()
    return {"status": "ok"}
