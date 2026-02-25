# DeskBot 桌面机器人

基于语音交互的桌面机器人项目，集成了 ASR (语音识别)、LLM (大语言模型) 和 TTS (语音合成) 功能。

## 功能架构

```
用户语音 → Whisper(ASR) → LLM(GPT/MiniMax) → CosyVoice(TTS) → 用户
```

## 技术栈

| 模块 | 技术 |
|------|------|
| ASR | OpenAI Whisper |
| LLM | OpenAI GPT-4o / MiniMax |
| TTS | CosyVoice (FunAudioLLM) |
| 通信 | WebSocket |
| 音频 | PyAudio, NumPy |

## 项目结构

```
deskbot/
├── server/           # Python 服务器
│   ├── ai/          # AI 模块 (asr, llm, tts)
│   ├── config/      # 配置管理
│   ├── core/        # 核心逻辑 (pipeline, vad)
│   ├── skills/      # 技能插件 (天气查询等)
│   └── network/     # 网络模块
├── CosyVoice/       # 语音合成子模块
├── esp32/           # ESP32 固件
├── tests/           # 测试目录
└── assets/          # 资源文件
```

## 快速开始

### 环境要求

- Python 3.10+
- Conda (推荐)
- ESP-IDF (用于编译 ESP32 固件)

### 1. 创建 conda 环境

```bash
conda create -n deskbot python=3.10 -y
conda activate deskbot
```

### 2. 安装主项目依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 CosyVoice 依赖

```bash
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt
```

### 4. 下载 TTS 模型

```python
from modelscope import snapshot_download

# 下载 CosyVoice 模型
snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512',
                  local_dir='pretrained_models/Fun-CosyVoice3-0.5B')
snapshot_download('iic/CosyVoice-ttsfrd',
                  local_dir='pretrained_models/CosyVoice-ttsfrd')
```

### 5. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

主要配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 (openai/minimax) | minimax |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `MINIMAX_API_KEY` | MiniMax API 密钥 | - |
| `MODEL_NAME` | LLM 模型名称 | gpt-4o-mini |
| `ASR_MODEL` | Whisper 模型大小 | base |
| `COSYVOICE_PATH` | CosyVoice 仓库路径 | ./CosyVoice |
| `COSYVOICE_MODEL` | TTS 模型名称 | CosyVoice-300M |
| `SERVER_PORT` | WebSocket 服务端口 | 8765 |

### 6. 运行服务

```bash
python -m server.main
# 或使用 run.sh
./run.sh
```

## WebSocket API

连接地址: `ws://localhost:8765`

### 客户端示例 (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  console.log('Connected to DeskBot');
  // 发送音频数据
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## ESP32 固件

### 构建

```bash
cd esp32
. ~/esp/esp-idf/export.sh
idf.py build
```

### 烧录

```bash
idf.py -p /dev/ttyUSB0 flash
```

## 可用技能

- **天气查询**: 查询指定城市的天气情况

## 许可证

MIT License
