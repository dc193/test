# 本地 Whisper 语音转文字服务

这是一个简单的本地服务，使用 OpenAI Whisper 将视频/音频转换为文字。

## 优点

- **无需复杂配置**：不需要 Chrome 扩展的各种权限问题
- **模型本地存储**：Whisper 模型下载一次后永久保存在本地
- **更稳定**：没有浏览器扩展的 CSP 限制
- **更强大**：可以使用更大的模型获得更好的效果

## 安装

### 1. 安装依赖

```bash
# 创建虚拟环境（可选但推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install flask flask-cors openai-whisper
```

### 2. 运行服务

```bash
python server.py
```

首次运行会自动下载 Whisper 模型（约 500MB-1GB，取决于模型大小）。

### 3. 打开浏览器

访问 http://localhost:5000

## 使用方法

1. 点击 **"开始录制"**
2. 在弹出的对话框中选择要录制的 **标签页** 或 **整个屏幕**
3. **重要**：勾选 **"共享标签页音频"** 或 **"共享系统音频"**
4. 播放视频
5. 录制完成后点击 **"停止录制"**
6. 等待转录完成

## 模型选择

默认使用 `small` 模型，平衡了速度和准确性。

在 `server.py` 中可以修改模型：

```python
model_name = "small"  # 可选: tiny, base, small, medium, large
```

| 模型 | 大小 | 速度 | 准确性 |
|------|------|------|--------|
| tiny | ~75MB | 最快 | 一般 |
| base | ~150MB | 快 | 较好 |
| small | ~500MB | 中等 | 好 |
| medium | ~1.5GB | 慢 | 很好 |
| large | ~3GB | 最慢 | 最好 |

## 注意事项

- 首次运行需要下载模型，请耐心等待
- 模型下载后保存在 `~/.cache/whisper/` 目录
- 需要在 Chrome/Edge/Firefox 中使用（支持 getDisplayMedia API）
- 选择共享时必须勾选"共享音频"选项

## 问题排查

**Q: 录制后没有转录结果？**
A: 确保选择了"共享标签页音频"选项。

**Q: 转录不准确？**
A: 尝试使用更大的模型（medium 或 large）。

**Q: 服务启动很慢？**
A: 首次启动需要下载模型，之后会很快。
