# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

这是一个桌面机器人 (Desk Robot) 项目，集成了语音交互功能。核心数据流：

```
用户语音 → Whisper(ASR) → OpenAI(LLM) → CosyVoice(TTS) → 用户
```

## 常用命令

### 环境设置 (使用 conda)
```bash
# 创建并激活 conda 环境
conda create -n deskbot python=3.10 -y
conda activate deskbot

# 安装主项目依赖
pip install -r requirements.txt

# 克隆并安装 CosyVoice 子模块
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
pip install -r requirements.txt
```

### CosyVoice 模型下载
```python
from modelscope import snapshot_download
snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')
snapshot_download('iic/CosyVoice-ttsfrd', local_dir='pretrained_models/CosyVoice-ttsfrd')
```

### CosyVoice 运行
```bash
# 基本示例
python CosyVoice/example.py

# Web UI
python CosyVoice/webui.py --port 50000 --model_dir pretrained_models/CosyVoice-300M

# Docker 部署
cd CosyVoice/runtime/python && docker build -t cosyvoice:v1.0 .
```

### ESP32 固件构建
```bash
# 设置 ESP-IDF 环境并编译 (需要在 esp32 目录下执行)
. ~/esp/esp-idf/export.sh && idf.py build

# 烧录固件 (替换 /dev/ttyUSB0 为实际串口)
idf.py -p /dev/ttyUSB0 flash
```

### ESP-IDF 环境设置
```bash
# 首次设置 ESP-IDF
cd ~/esp/esp-idf
./install.sh esp32

# 每次使用前激活环境
. ~/esp/esp-idf/export.sh
```

## 环境变量

复制 `.env.example` 为 `.env` 并配置：
- `OPENAI_API_KEY`: OpenAI API 密钥
- `MODEL_NAME`: LLM 模型名称 (默认 gpt-4o-mini)
- `ASR_MODEL`: Whisper 模型大小 (默认 base)
- `COSYVOICE_PATH`: CosyVoice 仓库路径
- `COSYVOICE_MODEL`: TTS 模型名称

## Architecture

```
deskbot/
├── server/           # Python 服务器 (空框架，待实现)
│   ├── ai/          # AI 模块
│   ├── config/      # 配置模块
│   ├── core/        # 核心模块
│   └── network/     # 网络模块
├── CosyVoice/       # 语音合成子模块 (FunAudioLLM)
│   ├── cosyvoice/   # 核心库
│   ├── example.py   # 使用示例
│   └── runtime/     # 部署脚本
├── esp32/           # ESP32 固件 (C/CMake)
├── tests/           # 测试目录
└── assets/          # 资源文件
```

### 技术栈
- **ASR**: OpenAI Whisper
- **LLM**: OpenAI GPT-4o-mini (可配置)
- **TTS**: CosyVoice (Fun-CosyVoice3 / CosyVoice2 / CosyVoice1)
- **WebSocket**: websockets>=12.0
- **音频**: pyaudio, numpy

### 关键约束
- CosyVoice 依赖需要在 `CosyVoice/` 目录内单独安装
- TTS 模型需要手动从 ModelScope 或 HuggingFace 下载
- ESP32 构建需要 ESP-IDF 环境
