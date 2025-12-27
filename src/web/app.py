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
from ..core.llm import get_available_providers, create_llm_provider
from ..roles.ceo import CEO
from ..roles.chro import CHRO
from ..roles.coo import COO
from ..memory.store import LocalMemoryStore


app = FastAPI(title="AI Company", version="0.1.0")

# 全局状态
company_instance: Optional[Company] = None
current_provider: str = "openai"
websocket_connections: list[WebSocket] = []


def get_company(provider_name: Optional[str] = None) -> Company:
    """获取或创建公司实例"""
    global company_instance, current_provider

    # 如果provider变了，重新创建
    if provider_name and provider_name != current_provider:
        company_instance = None
        current_provider = provider_name

    if company_instance is None:
        try:
            llm = create_llm_provider(current_provider)
        except ValueError as e:
            # 如果当前provider没有key，尝试找一个有key的
            providers = get_available_providers()
            for p in providers:
                if p["has_key"]:
                    current_provider = p["name"]
                    llm = create_llm_provider(current_provider)
                    break
            else:
                raise ValueError("没有可用的LLM Provider，请设置API Key")

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
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Company v0.1</h1>
        <div class="header-right">
            <div class="provider-select">
                <label>模型:</label>
                <select id="provider-select" onchange="changeProvider()">
                    <option value="openai">OpenAI (GPT-4)</option>
                    <option value="claude">Claude</option>
                    <option value="gemini">Gemini</option>
                    <option value="grok">Grok</option>
                    <option value="qwen">Qwen (通义)</option>
                    <option value="local">本地 (Ollama)</option>
                </select>
                <span class="current-provider" id="current-provider">-</span>
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
        const providerSelect = document.getElementById('provider-select');
        const currentProviderEl = document.getElementById('current-provider');

        let ws = null;

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

        async function loadProviders() {
            try {
                const response = await fetch('/api/providers');
                const providers = await response.json();

                providerSelect.innerHTML = providers.map(p =>
                    `<option value="${p.name}" ${!p.has_key ? 'disabled' : ''}>${p.name.toUpperCase()}${!p.has_key ? ' (无Key)' : ''}</option>`
                ).join('');

                // 选中当前provider
                const statusResp = await fetch('/api/status');
                const status = await statusResp.json();
                if (status.current_provider) {
                    providerSelect.value = status.current_provider;
                    currentProviderEl.textContent = status.current_provider;
                }
            } catch (e) { console.error(e); }
        }

        async function changeProvider() {
            const provider = providerSelect.value;
            if (!confirm(`切换到 ${provider.toUpperCase()} 将重置当前对话，确定吗？`)) {
                updateStatus();
                return;
            }

            try {
                await fetch('/api/provider', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider })
                });
                currentProviderEl.textContent = provider;
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
        loadProviders();
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


@app.get("/api/providers")
async def list_providers():
    """获取所有可用的Provider"""
    return get_available_providers()


@app.post("/api/provider")
async def set_provider(request: dict):
    """切换Provider"""
    global company_instance, current_provider
    provider = request.get("provider", "openai")

    # 重置公司实例
    company_instance = None
    current_provider = provider

    # 尝试创建新实例
    try:
        get_company(provider)
        return {"status": "ok", "provider": provider}
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
    ceo = company.get_agent("ceo")
    coo = company.get_agent("coo")

    return {
        "ceo_state": ceo.state,
        "current_provider": current_provider,
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
