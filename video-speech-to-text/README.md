# Video Speech to Text - Chrome 视频语音转文字插件

这是一个 Chrome 浏览器扩展，可以直接捕获标签页音频并使用本地 AI 模型（Whisper）转换成文字。

## 功能特点

- **系统音频捕获**：直接捕获标签页音频，不受外部环境噪音干扰
- **本地 AI 转录**：使用 Whisper 模型在本地处理，无需网络，保护隐私
- **支持多种语言**：中文、英文、日语、韩语等
- **后台运行**：可以在录制时操作其他网页
- **悬浮面板**：方便的悬浮面板界面，可拖动、最小化
- **一键操作**：复制文本或保存为 TXT 文件
- **免费使用**：无需 API 密钥，完全免费

## 安装方法

### 1. 下载/克隆插件文件

确保你有以下文件：
```
video-speech-to-text/
├── manifest.json
├── popup.html
├── popup.css
├── popup.js
├── background.js
├── content.js
├── content.css
├── offscreen.html
├── offscreen.js
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md
```

### 2. 生成图标（首次安装需要）

1. 用浏览器打开 `generate-icons.html` 文件
2. 点击每个图标下方的"下载"按钮
3. 将下载的图标保存到 `icons` 文件夹中

### 3. 安装到 Chrome

1. 打开 Chrome 浏览器
2. 在地址栏输入 `chrome://extensions/` 并回车
3. 开启右上角的 **"开发者模式"**
4. 点击 **"加载已解压的扩展程序"**
5. 选择 `video-speech-to-text` 文件夹
6. 安装完成！

## 使用方法

1. 打开包含视频的网页（如 YouTube、Bilibili 等）
2. 播放视频
3. 点击浏览器工具栏中的插件图标，或使用页面上的悬浮面板
4. 选择识别语言
5. 点击 **"开始录制"** 按钮
6. 首次使用时会自动下载 Whisper 模型（约 150MB），请耐心等待
7. 模型加载完成后，插件会开始识别视频中的语音
8. 录制完成后，点击 **"停止录制"**
9. 可以选择 **"复制文本"** 或 **"保存文件"**

## 技术特点

- **tabCapture API**：使用 Chrome 的 tabCapture API 直接捕获标签页音频流
- **Offscreen Document**：使用 offscreen document 在后台处理音频
- **Whisper WASM**：使用 transformers.js 在浏览器中运行 Whisper 模型
- **本地处理**：所有音频处理和转录都在本地完成，不上传到任何服务器

## 注意事项

- **首次加载**：首次使用时需要下载 Whisper 模型（约 150MB），之后会缓存在浏览器中
- **处理延迟**：由于是本地 AI 处理，转录结果会有几秒延迟
- **标签页音频**：只能捕获当前标签页的音频，其他标签页或系统音频不会被录制
- **Chrome 限制**：需要 Chrome 116 或更高版本

## 与旧版本的区别

| 功能 | 旧版本 (v1.0) | 新版本 (v2.0) |
|------|--------------|---------------|
| 音频来源 | 麦克风 | 标签页音频 |
| 外部噪音干扰 | 会受干扰 | 不受干扰 |
| 网络需求 | 需要（Google API） | 不需要 |
| 转录引擎 | Web Speech API | Whisper (本地) |
| 隐私保护 | 音频上传到 Google | 完全本地处理 |

## 常见问题

**Q: 首次使用时加载很慢？**
A: 首次使用需要下载 Whisper 模型（约 150MB），之后会缓存在浏览器中，下次使用会很快。

**Q: 为什么转录有延迟？**
A: 本地 AI 处理需要一定时间，每 5 秒的音频会批量处理一次。

**Q: 支持离线使用吗？**
A: 模型下载后支持完全离线使用。

**Q: 可以录制其他标签页的声音吗？**
A: 不可以，Chrome 的 tabCapture API 只能捕获当前活动标签页的音频。

## 技术栈

- Chrome Extension Manifest V3
- Chrome tabCapture API
- Chrome Offscreen Documents API
- Whisper (via transformers.js)
- 原生 JavaScript

## 许可证

MIT License
