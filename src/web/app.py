"""Web应用 - AI Company完整界面"""
from dotenv import load_dotenv
load_dotenv()  # 确保环境变量被加载

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import json
import asyncio
from typing import Optional

from ..core.company import Company, AgentInfo, AgentStatus
from ..core.message import Message
from ..core.llm import get_available_providers, create_llm_provider, get_all_available_models
from ..roles.ceo import CEO
from ..roles.chro import CHRO
from ..roles.coo import COO
from ..memory.store import LocalMemoryStore


app = FastAPI(title="AI Company", version="0.1.0")

# 全局状态
company_instance: Optional[Company] = None
current_provider: Optional[str] = None  # 不预设默认，让用户选择
current_model: Optional[str] = None  # 当前选择的模型
websocket_connections: list[WebSocket] = []


def get_company(provider_name: Optional[str] = None, model_id: Optional[str] = None) -> Optional[Company]:
    """获取或创建公司实例"""
    global company_instance, current_provider, current_model

    # 如果还没选择provider，返回None
    if provider_name is None and current_provider is None:
        return None

    # 如果provider或model变了，重新创建
    if (provider_name and provider_name != current_provider) or (model_id and model_id != current_model):
        company_instance = None
        if provider_name:
            current_provider = provider_name
        if model_id:
            current_model = model_id

    if company_instance is None:
        if current_provider is None:
            raise ValueError("请先选择一个LLM Provider")

        llm = create_llm_provider(current_provider, model_id=current_model)

        company_instance = Company(llm=llm)
        company_instance.memory = LocalMemoryStore()

        # 创建并注册agents
        ceo = CEO(company_instance)
        company_instance.register_agent("ceo", ceo, AgentInfo(id="ceo", name="CEO", role="ceo", level=1))

        chro = CHRO(company_instance)
        company_instance.register_agent("chro", chro, AgentInfo(id="chro", name="CHRO", role="chro", level=1))

        coo = COO(company_instance)
        company_instance.register_agent("coo", coo, AgentInfo(id="coo", name="COO", role="coo", level=1))

        async def on_message(message: Message):
            await broadcast_message(message)
        company_instance.bus.set_user_callback(on_message)

    return company_instance


async def broadcast_message(message: Message):
    """广播消息给所有WebSocket连接"""
    data = {"type": "message", "data": message.to_dict()}
    for ws in websocket_connections:
        try:
            await ws.send_json(data)
        except:
            pass


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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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
        .header h1 { font-size: 1.5rem; color: #e94560; }
        .header-right { display: flex; gap: 1rem; align-items: center; }
        .god-link {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: #fff;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        .god-link:hover { opacity: 0.85; }
        .status { font-size: 0.9rem; color: #888; }
        .status .state { color: #4ecca3; font-weight: bold; }

        /* Provider选择器 */
        .provider-select {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .provider-select label {
            font-size: 0.85rem;
            color: #888;
        }
        .provider-select select {
            padding: 0.4rem 0.8rem;
            border: 1px solid #0f3460;
            border-radius: 6px;
            background: #0f3460;
            color: #eee;
            font-size: 0.85rem;
            cursor: pointer;
        }
        .provider-select select:focus { outline: 2px solid #e94560; }
        .provider-select select option { background: #16213e; }
        .provider-select select option:disabled { color: #555; }

        .main-container {
            flex: 1;
            display: flex;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 1rem;
            gap: 1rem;
        }

        .chat-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #16213e;
            border-radius: 12px;
            padding: 1rem;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            max-height: calc(100vh - 300px);
        }
        .message { margin-bottom: 1rem; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message .role { font-size: 0.8rem; font-weight: bold; margin-bottom: 0.3rem; }
        .message.user .role { color: #4ecca3; }
        .message.ceo .role { color: #e94560; }
        .message.system .role { color: #ffd700; }
        .message .content {
            background: #0f3460;
            padding: 0.8rem 1rem;
            border-radius: 8px;
            line-height: 1.5;
            white-space: pre-wrap;
            font-size: 0.95rem;
        }
        .message.user .content { border-left: 3px solid #4ecca3; }
        .message.ceo .content { border-left: 3px solid #e94560; }
        .message.system .content { border-left: 3px solid #ffd700; background: #2a2a4a; }

        .input-area {
            display: flex;
            gap: 0.5rem;
            padding-top: 1rem;
            border-top: 1px solid #0f3460;
        }
        .input-area textarea {
            flex: 1;
            padding: 0.8rem;
            border: none;
            border-radius: 8px;
            background: #0f3460;
            color: #eee;
            font-size: 0.95rem;
            resize: none;
            min-height: 50px;
        }
        .input-area textarea:focus { outline: 2px solid #e94560; }
        .input-area button {
            padding: 0.8rem 1.5rem;
            border: none;
            border-radius: 8px;
            background: #e94560;
            color: white;
            cursor: pointer;
            transition: background 0.2s;
        }
        .input-area button:hover { background: #ff6b6b; }
        .input-area button:disabled { background: #555; cursor: not-allowed; }

        .actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        .actions button {
            padding: 0.4rem 0.8rem;
            border: 1px solid #0f3460;
            border-radius: 6px;
            background: transparent;
            color: #888;
            font-size: 0.8rem;
            cursor: pointer;
        }
        .actions button:hover { border-color: #e94560; color: #e94560; }

        .status-panel {
            width: 300px;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .panel {
            background: #16213e;
            border-radius: 12px;
            padding: 1rem;
        }
        .panel h3 {
            font-size: 0.9rem;
            color: #e94560;
            margin-bottom: 0.8rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #0f3460;
        }

        .team-member {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            border-radius: 6px;
            margin-bottom: 0.3rem;
            background: #0f3460;
        }
        .team-member .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #888;
        }
        .team-member .dot.working { background: #4ecca3; animation: pulse 1s infinite; }
        .team-member .dot.idle { background: #888; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .team-member .name { font-size: 0.85rem; flex: 1; }
        .team-member .task { font-size: 0.7rem; color: #888; }

        .progress-bar {
            height: 8px;
            background: #0f3460;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }
        .progress-bar .fill {
            height: 100%;
            background: #4ecca3;
            transition: width 0.3s;
        }
        .progress-text {
            font-size: 0.8rem;
            color: #888;
            text-align: center;
        }

        .task-item {
            padding: 0.5rem;
            border-radius: 6px;
            margin-bottom: 0.3rem;
            background: #0f3460;
            font-size: 0.8rem;
        }
        .task-item.completed { opacity: 0.6; }
        .task-item .task-status {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        .task-item .task-status.pending { background: #888; }
        .task-item .task-status.in_progress { background: #ffd700; }
        .task-item .task-status.completed { background: #4ecca3; }

        .typing::after { content: '...'; animation: typing 1s infinite; }
        @keyframes typing {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        /* 当前Provider显示 */
        .current-provider {
            font-size: 0.75rem;
            color: #4ecca3;
            padding: 0.2rem 0.5rem;
            background: #0f3460;
            border-radius: 4px;
        }

        /* Provider选择界面 */
        .provider-selection-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .provider-selection-overlay.hidden { display: none; }
        .provider-selection-box {
            background: #16213e;
            border-radius: 16px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            text-align: center;
        }
        .provider-selection-box h2 {
            color: #e94560;
            margin-bottom: 0.5rem;
        }
        .provider-selection-box p {
            color: #888;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }
        .provider-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .provider-btn {
            padding: 1rem;
            border: 2px solid #0f3460;
            border-radius: 10px;
            background: #0f3460;
            color: #eee;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .provider-btn:hover:not(:disabled) {
            border-color: #e94560;
            background: #1a1a3e;
        }
        .provider-btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }
        .provider-btn .provider-name { font-weight: bold; }
        .provider-btn .provider-status {
            font-size: 0.8rem;
            color: #4ecca3;
        }
        .provider-btn:disabled .provider-status { color: #888; }

        /* 模型分组样式 */
        .model-group {
            margin-bottom: 1rem;
            text-align: left;
        }
        .model-group-title {
            font-size: 0.85rem;
            color: #e94560;
            margin-bottom: 0.5rem;
            padding-bottom: 0.3rem;
            border-bottom: 1px solid #0f3460;
        }
        .model-btn {
            width: 100%;
            padding: 0.8rem 1rem;
            margin-bottom: 0.3rem;
            border: 1px solid #0f3460;
            border-radius: 8px;
            background: #0f3460;
            color: #eee;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
            text-align: left;
        }
        .model-btn:hover {
            border-color: #e94560;
            background: #1a1a3e;
        }
        .model-btn .model-name { font-weight: bold; }
        .model-btn .model-desc {
            font-size: 0.75rem;
            color: #888;
        }
        .provider-selection-box {
            max-height: 80vh;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <!-- 模型选择界面 -->
    <div class="provider-selection-overlay" id="provider-overlay">
        <div class="provider-selection-box">
            <h2>AI Company v0.1</h2>
            <p>选择一个模型开始使用</p>
            <div class="provider-list" id="provider-list">
                <!-- 动态加载模型列表 -->
                <div style="color: #888;">加载中...</div>
            </div>
        </div>
    </div>

    <div class="header">
        <h1>AI Company v0.1</h1>
        <div class="header-right">
            <a href="/god" class="god-link">God Layer</a>
            <div class="provider-select">
                <label>模型:</label>
                <select id="model-select" onchange="changeModel()">
                    <!-- 动态加载 -->
                </select>
                <span class="current-provider" id="current-model-display">-</span>
            </div>
            <div class="status">状态: <span class="state" id="state">等待中</span></div>
        </div>
    </div>

    <div class="main-container">
        <div class="chat-section">
            <div class="messages" id="messages">
                <div class="message ceo">
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
                <button onclick="sendCommand('暂停')">暂停</button>
                <button onclick="sendCommand('继续')">继续</button>
            </div>
        </div>

        <div class="status-panel">
            <div class="panel">
                <h3>团队成员</h3>
                <div id="team-list">
                    <div class="team-member">
                        <span class="dot idle"></span>
                        <span class="name">CEO</span>
                        <span class="task">待命</span>
                    </div>
                </div>
            </div>

            <div class="panel">
                <h3>执行进度</h3>
                <div class="progress-bar">
                    <div class="fill" id="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-text" id="progress-text">暂无任务</div>
            </div>

            <div class="panel">
                <h3>任务列表</h3>
                <div id="task-list">
                    <div style="color: #888; font-size: 0.8rem;">暂无任务</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('input');
        const sendBtn = document.getElementById('send');
        const stateEl = document.getElementById('state');
        const teamListEl = document.getElementById('team-list');
        const progressFillEl = document.getElementById('progress-fill');
        const progressTextEl = document.getElementById('progress-text');
        const taskListEl = document.getElementById('task-list');
        const modelSelect = document.getElementById('model-select');
        const currentModelDisplay = document.getElementById('current-model-display');
        const providerOverlay = document.getElementById('provider-overlay');
        const providerListEl = document.getElementById('provider-list');

        let ws = null;
        let modelSelected = false;
        let allModels = [];  // 缓存所有模型数据

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'message') handleSystemMessage(data.data);
                else if (data.type === 'status') updateStatusPanel(data.data);
            };
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }

        function handleSystemMessage(msg) {
            if (msg.from_agent !== 'user' && msg.from_agent !== 'ceo') {
                addMessage('system', `[${msg.from_agent}] ${msg.content}`, msg.from_agent);
            }
        }

        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        async function sendMessage() {
            const message = inputEl.value.trim();
            if (!message) return;

            inputEl.disabled = true;
            sendBtn.disabled = true;
            addMessage('user', message);
            inputEl.value = '';

            const assistantMsg = addMessage('ceo', '<span class="typing"></span>', 'ceo', true);

            try {
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
                    fullContent += decoder.decode(value);
                    assistantMsg.querySelector('.content').textContent = fullContent;
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                }
                updateStatus();
            } catch (error) {
                assistantMsg.querySelector('.content').textContent = '出错了: ' + error.message;
            }

            inputEl.disabled = false;
            sendBtn.disabled = false;
            inputEl.focus();
        }

        async function sendCommand(cmd) {
            await fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
            updateStatus();
        }

        function addMessage(role, content, agent = '', isHtml = false) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            const roleName = role === 'user' ? '你' : (agent || 'CEO').toUpperCase();
            div.innerHTML = `
                <div class="role">${roleName}</div>
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

        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateStatusPanel(data);
            } catch (e) { console.error(e); }
        }

        function updateStatusPanel(data) {
            const stateMap = {
                'idle': '等待中',
                'exploring': '需求探索中',
                'planning': '计划制定中',
                'executing': '执行中',
                'reviewing': '验收中'
            };
            stateEl.textContent = stateMap[data.ceo_state] || data.ceo_state || '等待中';

            // 更新当前provider显示
            if (data.current_provider) {
                currentProviderEl.textContent = data.current_provider;
                providerSelect.value = data.current_provider;
            }

            if (data.agents) {
                teamListEl.innerHTML = data.agents.map(agent => `
                    <div class="team-member">
                        <span class="dot ${agent.status === 'working' ? 'working' : 'idle'}"></span>
                        <span class="name">${agent.name}</span>
                        <span class="task">${agent.current_task || '待命'}</span>
                    </div>
                `).join('');
            }

            if (data.progress) {
                const percent = data.progress.progress_percent || 0;
                progressFillEl.style.width = percent + '%';
                progressTextEl.textContent = `${data.progress.completed || 0}/${data.progress.total_tasks || 0} 完成`;

                if (data.progress.tasks && data.progress.tasks.length > 0) {
                    taskListEl.innerHTML = data.progress.tasks.map(task => `
                        <div class="task-item ${task.status}">
                            <span class="task-status ${task.status}"></span>
                            ${task.description}
                        </div>
                    `).join('');
                } else {
                    taskListEl.innerHTML = '<div style="color: #888; font-size: 0.8rem;">暂无任务</div>';
                }
            }
        }

        async function loadModels() {
            try {
                const response = await fetch('/api/models');
                allModels = await response.json();

                // 更新初始选择界面 - 按Provider分组显示模型
                if (allModels.length === 0) {
                    providerListEl.innerHTML = '<div style="color: #888;">未找到可用模型，请配置API Key</div>';
                    return;
                }

                let html = '';
                allModels.forEach(group => {
                    html += `<div class="model-group">
                        <div class="model-group-title">${group.provider_display}</div>`;
                    group.models.forEach(model => {
                        html += `<button class="model-btn" onclick="selectModel('${group.provider}', '${model.id}')">
                            <span class="model-name">${model.name}</span>
                            <span class="model-desc">${model.description || ''}</span>
                        </button>`;
                    });
                    html += '</div>';
                });
                providerListEl.innerHTML = html;

                // 更新header中的下拉选择
                let selectHtml = '';
                allModels.forEach(group => {
                    selectHtml += `<optgroup label="${group.provider_display}">`;
                    group.models.forEach(model => {
                        selectHtml += `<option value="${group.provider}|${model.id}">${model.name}</option>`;
                    });
                    selectHtml += '</optgroup>';
                });
                modelSelect.innerHTML = selectHtml;

                // 检查是否已选择模型
                const statusResp = await fetch('/api/status');
                const status = await statusResp.json();

                if (status.need_provider_selection) {
                    providerOverlay.classList.remove('hidden');
                    modelSelected = false;
                } else {
                    providerOverlay.classList.add('hidden');
                    modelSelected = true;
                    if (status.current_model) {
                        currentModelDisplay.textContent = status.current_model;
                        modelSelect.value = status.current_provider + '|' + status.current_model;
                    }
                }
            } catch (e) {
                console.error(e);
                providerListEl.innerHTML = '<div style="color: #e94560;">加载模型列表失败</div>';
            }
        }

        async function selectModel(provider, modelId) {
            try {
                const resp = await fetch('/api/provider', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider, model: modelId })
                });
                const result = await resp.json();

                if (result.status === 'ok') {
                    providerOverlay.classList.add('hidden');
                    modelSelected = true;
                    currentModelDisplay.textContent = modelId;
                    modelSelect.value = provider + '|' + modelId;
                    resetChatUI();
                } else {
                    alert('选择失败: ' + result.message);
                }
            } catch (e) {
                alert('选择失败: ' + e.message);
            }
        }

        async function changeModel() {
            const value = modelSelect.value;
            const [provider, modelId] = value.split('|');
            if (!confirm(`切换到 ${modelId} 将重置当前对话，确定吗？`)) {
                updateStatus();
                return;
            }

            try {
                await fetch('/api/provider', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider, model: modelId })
                });
                currentModelDisplay.textContent = modelId;
                resetChatUI();
            } catch (e) {
                alert('切换失败: ' + e.message);
            }
        }

        function resetChatUI() {
            messagesEl.innerHTML = `
                <div class="message ceo">
                    <div class="role">CEO</div>
                    <div class="content">你好！我是这家AI公司的CEO。

告诉我你想做什么，我会帮你把想法变成可执行的计划。

你有什么想法？</div>
                </div>
            `;
            updateStatus();
        }

        async function resetChat() {
            if (!confirm('确定要重新开始吗？')) return;
            await fetch('/api/reset', { method: 'POST' });
            resetChatUI();
        }

        // 初始化
        connectWebSocket();
        loadModels();
        updateStatus();
        inputEl.focus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)


@app.get("/god", response_class=HTMLResponse)
async def god_layer_page():
    """God Layer 管理页面 - 知识库、学习、记忆管理"""
    html_content = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>God Layer - AI Company</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0a0a1a;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }
        h1 {
            color: #00d4ff;
            font-size: 1.8em;
        }
        h1 span { color: #666; font-weight: normal; }
        .back-btn {
            background: #333;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
        }
        .back-btn:hover { background: #444; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }
        .card {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #333;
        }
        .card h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 1.2em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card h2 .icon { font-size: 1.4em; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .stat-item {
            background: #252540;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            color: #00d4ff;
            font-weight: bold;
        }
        .stat-label {
            color: #888;
            font-size: 0.85em;
            margin-top: 5px;
        }

        input, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #333;
            border-radius: 6px;
            background: #252540;
            color: #fff;
            font-size: 14px;
            margin-bottom: 10px;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #00d4ff;
        }
        textarea { resize: vertical; min-height: 100px; }

        button {
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: #000;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            width: 100%;
            margin-top: 10px;
        }
        button:hover { opacity: 0.9; }
        button:disabled {
            background: #333;
            color: #666;
            cursor: not-allowed;
        }
        button.secondary {
            background: #333;
            color: #fff;
        }

        .results {
            margin-top: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        .result-item {
            background: #252540;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 3px solid #00d4ff;
        }
        .result-title {
            color: #00d4ff;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .result-content {
            color: #aaa;
            font-size: 0.9em;
            white-space: pre-wrap;
            max-height: 100px;
            overflow: hidden;
        }
        .result-meta {
            display: flex;
            gap: 15px;
            margin-top: 8px;
            font-size: 0.8em;
            color: #666;
        }
        .result-score {
            color: #4caf50;
        }

        .status {
            padding: 10px;
            border-radius: 6px;
            margin-top: 10px;
            display: none;
        }
        .status.success { background: #1b4332; color: #4caf50; display: block; }
        .status.error { background: #4a1c1c; color: #f44336; display: block; }
        .status.loading { background: #1a3a5c; color: #00d4ff; display: block; }

        .tag {
            display: inline-block;
            background: #333;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-right: 5px;
        }

        select {
            width: 100%;
            padding: 12px;
            border: 1px solid #333;
            border-radius: 6px;
            background: #252540;
            color: #fff;
            font-size: 14px;
            margin-bottom: 10px;
        }

        .type-list {
            margin-top: 10px;
        }
        .type-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #333;
        }
        .type-item:last-child { border-bottom: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>God Layer <span>/ 上帝层管理</span></h1>
            <a href="/" class="back-btn">← 返回 AI Company</a>
        </header>

        <div class="grid">
            <!-- 知识库统计 -->
            <div class="card">
                <h2><span class="icon">📊</span> 知识库统计</h2>
                <div class="stats-grid" id="stats">
                    <div class="stat-item">
                        <div class="stat-value" id="total-count">-</div>
                        <div class="stat-label">总知识数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="type-count">-</div>
                        <div class="stat-label">知识类型</div>
                    </div>
                </div>
                <div class="type-list" id="type-list"></div>
                <button class="secondary" onclick="loadStats()">刷新统计</button>
            </div>

            <!-- 搜索知识 -->
            <div class="card">
                <h2><span class="icon">🔍</span> 搜索知识</h2>
                <input type="text" id="search-query" placeholder="输入搜索内容...">
                <button onclick="searchKnowledge()">搜索</button>
                <div class="results" id="search-results"></div>
            </div>

            <!-- GitHub 学习 -->
            <div class="card">
                <h2><span class="icon">📚</span> 从 GitHub 学习</h2>
                <p style="color: #888; font-size: 0.85em; margin-bottom: 10px;">
                    AI 会分析仓库代码，提炼核心架构、设计模式和可复用经验
                </p>
                <input type="text" id="github-url" placeholder="https://github.com/user/repo">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <label style="color: #888; font-size: 0.85em; white-space: nowrap;">分析文件数:</label>
                    <input type="number" id="max-files" value="10" min="1" max="30" style="width: 80px;">
                </div>
                <button onclick="learnFromGithub()" id="learn-btn">AI 分析学习</button>
                <div class="status" id="learn-status"></div>
            </div>

            <!-- 添加知识 -->
            <div class="card">
                <h2><span class="icon">➕</span> 添加知识</h2>
                <input type="text" id="add-title" placeholder="标题">
                <select id="add-type">
                    <option value="best_practice">最佳实践</option>
                    <option value="code_pattern">代码模式</option>
                    <option value="project_experience">项目经验</option>
                    <option value="documentation">文档</option>
                    <option value="user_feedback">用户反馈</option>
                </select>
                <textarea id="add-content" placeholder="知识内容..."></textarea>
                <input type="text" id="add-tags" placeholder="标签（逗号分隔）">
                <button onclick="addKnowledge()">添加</button>
                <div class="status" id="add-status"></div>
            </div>
        </div>
    </div>

    <script>
        // 加载统计
        async function loadStats() {
            try {
                const resp = await fetch('/api/knowledge/stats');
                const data = await resp.json();

                if (data.error) {
                    document.getElementById('total-count').textContent = '!';
                    return;
                }

                document.getElementById('total-count').textContent = data.total || 0;
                document.getElementById('type-count').textContent = Object.keys(data.by_type || {}).length;

                // 显示类型分布
                const typeList = document.getElementById('type-list');
                const typeNames = {
                    'project_experience': '项目经验',
                    'code_pattern': '代码模式',
                    'best_practice': '最佳实践',
                    'user_feedback': '用户反馈',
                    'github_example': 'GitHub示例',
                    'documentation': '文档'
                };

                let html = '';
                for (const [type, count] of Object.entries(data.by_type || {})) {
                    html += `<div class="type-item">
                        <span>${typeNames[type] || type}</span>
                        <span>${count}</span>
                    </div>`;
                }
                typeList.innerHTML = html;

            } catch (e) {
                console.error(e);
            }
        }

        // 搜索知识
        async function searchKnowledge() {
            const query = document.getElementById('search-query').value;
            if (!query) return;

            const resultsEl = document.getElementById('search-results');
            resultsEl.innerHTML = '<div class="status loading">搜索中...</div>';

            try {
                const resp = await fetch('/api/knowledge/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, top_k: 10 })
                });
                const data = await resp.json();

                if (data.error || data.status === 'error') {
                    resultsEl.innerHTML = `<div class="status error">${data.error || data.message}</div>`;
                    return;
                }

                if (!data.results || data.results.length === 0) {
                    resultsEl.innerHTML = '<div class="status">没有找到相关知识</div>';
                    return;
                }

                let html = '';
                for (const r of data.results) {
                    html += `<div class="result-item">
                        <div class="result-title">${r.title || '无标题'}</div>
                        <div class="result-content">${escapeHtml(r.content)}</div>
                        <div class="result-meta">
                            <span class="tag">${r.type}</span>
                            <span class="result-score">相似度: ${(r.score * 100).toFixed(1)}%</span>
                            ${r.source ? `<span>来源: ${r.source}</span>` : ''}
                        </div>
                    </div>`;
                }
                resultsEl.innerHTML = html;

            } catch (e) {
                resultsEl.innerHTML = `<div class="status error">搜索失败: ${e.message}</div>`;
            }
        }

        // GitHub 学习
        async function learnFromGithub() {
            const url = document.getElementById('github-url').value;
            const maxFiles = document.getElementById('max-files').value;
            const statusEl = document.getElementById('learn-status');
            const btn = document.getElementById('learn-btn');

            if (!url) {
                statusEl.className = 'status error';
                statusEl.textContent = '请输入 GitHub URL';
                return;
            }

            btn.disabled = true;
            btn.textContent = 'AI 分析中...';
            statusEl.className = 'status loading';
            statusEl.textContent = '正在 Clone 仓库并用 AI 分析代码，这可能需要 1-2 分钟...';

            try {
                const resp = await fetch('/api/knowledge/learn-github', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, max_files: parseInt(maxFiles) })
                });
                const data = await resp.json();

                if (data.error || data.status === 'error') {
                    statusEl.className = 'status error';
                    statusEl.textContent = data.error || data.message;
                } else {
                    statusEl.className = 'status success';
                    let msg = `学习完成！分析了 ${data.files_read || data.files_analyzed} 个文件`;
                    if (data.analysis) {
                        msg += '，已提炼核心知识';
                    }
                    statusEl.textContent = msg;
                    loadStats();
                }

            } catch (e) {
                statusEl.className = 'status error';
                statusEl.textContent = `学习失败: ${e.message}`;
            }

            btn.disabled = false;
            btn.textContent = 'AI 分析学习';
        }

        // 添加知识
        async function addKnowledge() {
            const title = document.getElementById('add-title').value;
            const type = document.getElementById('add-type').value;
            const content = document.getElementById('add-content').value;
            const tagsStr = document.getElementById('add-tags').value;
            const statusEl = document.getElementById('add-status');

            if (!content) {
                statusEl.className = 'status error';
                statusEl.textContent = '内容不能为空';
                return;
            }

            const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(t => t) : [];

            try {
                const resp = await fetch('/api/knowledge/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, type, content, tags, source: 'user_input' })
                });
                const data = await resp.json();

                if (data.error || data.status === 'error') {
                    statusEl.className = 'status error';
                    statusEl.textContent = data.error || data.message;
                } else {
                    statusEl.className = 'status success';
                    statusEl.textContent = `添加成功！ID: ${data.id}`;
                    // 清空输入
                    document.getElementById('add-title').value = '';
                    document.getElementById('add-content').value = '';
                    document.getElementById('add-tags').value = '';
                    loadStats();
                }

            } catch (e) {
                statusEl.className = 'status error';
                statusEl.textContent = `添加失败: ${e.message}`;
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 回车搜索
        document.getElementById('search-query').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchKnowledge();
        });

        // 初始化
        loadStats();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/providers")
async def list_providers():
    """获取所有可用的Provider"""
    return get_available_providers()


@app.get("/api/models")
async def list_models():
    """获取所有可用的模型（按Provider分组）"""
    return get_all_available_models()


@app.post("/api/provider")
async def set_provider(request: dict):
    """切换Provider和模型"""
    global company_instance, current_provider, current_model
    provider = request.get("provider")
    model = request.get("model")

    # 重置公司实例
    company_instance = None
    if provider:
        current_provider = provider
    if model:
        current_model = model

    # 尝试创建新实例
    try:
        get_company(current_provider, current_model)
        return {"status": "ok", "provider": current_provider, "model": current_model}
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    company = get_company()
    ceo = company.get_agent("ceo")
    response = await ceo.chat(request.message)
    return {"response": response, "state": ceo.get_state()}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    company = get_company()
    if company is None:
        async def error_gen():
            yield "请先选择一个LLM Provider"
        return StreamingResponse(error_gen(), media_type="text/plain")

    ceo = company.get_agent("ceo")

    async def generate():
        async for chunk in ceo.stream_chat(request.message):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")


@app.get("/api/state")
async def get_state():
    company = get_company()
    ceo = company.get_agent("ceo")
    return ceo.get_state()


@app.get("/api/status")
async def get_status():
    company = get_company()

    # 如果还没选择provider
    if company is None:
        return {
            "ceo_state": None,
            "current_provider": None,
            "current_model": None,
            "need_provider_selection": True,
            "agents": [],
            "progress": None,
            "project": None
        }

    ceo = company.get_agent("ceo")
    coo = company.get_agent("coo")

    return {
        "ceo_state": ceo.state,
        "current_provider": current_provider,
        "current_model": current_model,
        "need_provider_selection": False,
        "agents": [
            {
                "id": info.id,
                "name": info.name,
                "role": info.role,
                "status": info.status.value,
                "current_task": info.current_task
            }
            for info in company.agent_info.values()
        ],
        "progress": coo.get_progress() if coo else None,
        "project": company.current_project
    }


@app.post("/api/command")
async def send_command(request: dict):
    company = get_company()
    command = request.get("command", "")
    message = Message(
        content=command,
        from_agent="user",
        to_agent="coo",
        msg_type="user_command"
    )
    await company.bus.publish(message)
    return {"status": "ok"}


@app.post("/api/reset")
async def reset():
    global company_instance
    company_instance = None
    websocket_connections.clear()
    return {"status": "ok"}


# ==================== 知识库 API ====================

@app.get("/api/knowledge/stats")
async def knowledge_stats():
    """获取知识库统计"""
    company = get_company()
    if company is None:
        return {"error": "请先选择模型"}

    try:
        kb = company.knowledge_base
        stats = kb.get_stats()
        return {"status": "ok", **stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/knowledge/search")
async def knowledge_search(request: dict):
    """搜索知识库"""
    company = get_company()
    if company is None:
        return {"error": "请先选择模型"}

    query = request.get("query", "")
    top_k = request.get("top_k", 5)
    knowledge_type = request.get("type")  # 可选过滤

    try:
        kb = company.knowledge_base
        results = kb.search(query, top_k=top_k)
        return {
            "status": "ok",
            "results": [
                {
                    "id": r.knowledge.id,
                    "title": r.knowledge.title,
                    "content": r.knowledge.content[:500] + "..." if len(r.knowledge.content) > 500 else r.knowledge.content,
                    "type": r.knowledge.knowledge_type.value,
                    "source": r.knowledge.source,
                    "score": round(r.relevance_score, 3)
                }
                for r in results
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/knowledge/add")
async def knowledge_add(request: dict):
    """添加知识"""
    company = get_company()
    if company is None:
        return {"error": "请先选择模型"}

    content = request.get("content", "")
    title = request.get("title", "")
    knowledge_type = request.get("type", "best_practice")
    source = request.get("source", "user_input")
    tags = request.get("tags", [])

    if not content:
        return {"status": "error", "message": "内容不能为空"}

    try:
        from ..memory import KnowledgeType
        kb = company.knowledge_base

        # 转换类型
        try:
            kt = KnowledgeType(knowledge_type)
        except ValueError:
            kt = KnowledgeType.BEST_PRACTICE

        knowledge = kb.add(
            content=content,
            knowledge_type=kt,
            title=title,
            source=source,
            tags=tags
        )

        return {"status": "ok", "id": knowledge.id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/knowledge/learn-github")
async def learn_from_github_api(request: dict):
    """从 GitHub 学习 - 用当前选择的 LLM 分析代码"""
    company = get_company()
    if company is None:
        return {"error": "请先选择模型"}

    repo_url = request.get("url", "")
    if not repo_url:
        return {"status": "error", "message": "请提供 GitHub URL"}

    try:
        from ..memory import GitHubLearner
        kb = company.knowledge_base

        # 传入 LLM provider，让 AI 分析代码
        learner = GitHubLearner(kb, llm_provider=company.llm)

        # 学习仓库 (async)
        result = await learner.learn_from_url(
            repo_url,
            max_code_files=request.get("max_files", 10),
            cleanup=True
        )

        return {"status": "ok", **result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
