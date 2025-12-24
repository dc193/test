# Video Speech to Text - Chrome 视频语音转文字插件

这是一个 Chrome 浏览器扩展，可以帮助你录制视频中的语音并转换成文字保存。

## 功能特点

- 实时语音识别转文字
- 支持多种语言（中文、英文、日语、韩语等）
- 转录文本实时显示
- 一键复制转录内容
- 保存为 TXT 文件
- 美观的用户界面

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
3. 点击浏览器工具栏中的插件图标
4. 选择识别语言
5. 点击 **"开始录制"** 按钮
6. 插件会开始识别视频中的语音并实时显示文字
7. 录制完成后，点击 **"停止录制"**
8. 可以选择 **"复制文本"** 或 **"保存文件"**

## 注意事项

- **麦克风权限**：首次使用时，浏览器会请求麦克风权限，请点击"允许"
- **音频来源**：此插件使用麦克风来捕获音频，所以：
  - 确保电脑扬声器正常播放视频声音
  - 或者使用虚拟音频设备将系统音频路由到麦克风输入
- **网络连接**：语音识别需要网络连接（使用 Google 语音识别 API）
- **识别准确性**：识别准确度取决于音频质量和语言复杂度

## 高级用法：捕获系统音频

如果你想直接捕获系统音频而不是通过麦克风，可以使用以下方法：

### Windows
- 使用 [VB-Cable](https://vb-audio.com/Cable/) 虚拟音频设备
- 将 VB-Cable 设置为默认播放设备
- 在 Chrome 麦克风权限中选择 VB-Cable

### macOS
- 使用 [BlackHole](https://github.com/ExistentialAudio/BlackHole) 虚拟音频设备
- 创建多输出设备同时输出到扬声器和 BlackHole
- 在 Chrome 麦克风权限中选择 BlackHole

### Linux
- 使用 PulseAudio 的 `module-loopback` 模块
- 或使用 `pavucontrol` 配置音频路由

## 常见问题

**Q: 为什么没有识别到任何文字？**
A: 检查麦克风权限是否已授予，音量是否足够大。

**Q: 识别不准确怎么办？**
A: 尝试选择正确的语言，提高音频质量，减少背景噪音。

**Q: 支持离线使用吗？**
A: 不支持，语音识别需要连接到 Google 服务器。

## 技术栈

- Chrome Extension Manifest V3
- Web Speech API (SpeechRecognition)
- Chrome Downloads API
- 原生 JavaScript

## 许可证

MIT License
