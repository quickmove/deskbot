# DeskRobot 项目进度报告

> 最后更新: 2026-02-25

## 项目概述

DeskRobot 是一个桌面机器人项目，集成了语音交互功能。核心数据流：

```
用户语音 → Whisper(ASR) → OpenAI/MiniMax(LLM) → CosyVoice(TTS) → 用户
```

---

## 一、项目结构

```
deskbot/
├── server/                    # Python 服务器
│   ├── __init__.py
│   ├── main.py                 # 入口文件
│   ├── audio_server.py         # WebSocket 服务器
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # 配置管理
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── asr.py             # Whisper ASR 语音识别
│   │   ├── llm.py             # LLM 对话 (支持 OpenAI/MiniMax)
│   │   └── tts.py            # CosyVoice TTS 语音合成
│   ├── core/
│   │   ├── __init__.py
│   │   ├── vad.py             # WebRTC VAD 语音活动检测
│   │   └── pipeline.py        # 音频处理流水线
│   └── skills/
│       ├── __init__.py
│       ├── manager.py         # 技能管理器
│       └── weather.py         # 天气查询技能
├── esp32/                     # ESP32 固件 (C/CMake)
│   ├── components/
│   │   ├── wifi/              # WiFi 组件
│   │   └── websocket/         # WebSocket 组件
│   ├── main/
│   └── build/                 # 构建输出
├── CosyVoice/                 # 语音合成子模块
│   ├── cosyvoice/             # 核心库
│   ├── pretrained_models/     # 预训练模型
│   └── example.py             # 使用示例
├── assets/                    # 资源文件
│   └── memory/                # 记忆存储
├── tests/                     # 测试目录 (待创建)
└── docs/                      # 文档
```

---

## 二、模块进度

### 2.1 配置模块 (server/config/)

| 功能 | 状态 | 说明 |
|------|------|------|
| 环境变量加载 | ✅ 完成 | 使用 dotenv 加载 .env 文件 |
| ServerConfig | ✅ 完成 | 服务器配置 (host, port) |
| AudioConfig | ✅ 完成 | 音频配置 (sample_rate, channels) |
| VADConfig | ✅ 完成 | VAD 配置 |
| ASRConfig | ✅ 完成 | ASR 配置 (model, language) |
| LLMConfig | ✅ 完成 | LLM 配置 (支持 OpenAI/MiniMax) |
| TTSConfig | ✅ 完成 | TTS 配置 (CosyVoice) |
| RobotConfig | ✅ 完成 | 机器人配置 (唤醒词、触发词) |

### 2.2 网络模块 (server/network/)

| 功能 | 状态 | 说明 |
|------|------|------|
| WebSocket 服务器 | ✅ 完成 | 使用 websockets 库 |
| 客户端连接管理 | ✅ 完成 | 处理连接/断开 |
| 二进制音频传输 | ✅ 完成 | 接收/发送 PCM 音频 |
| JSON 消息处理 | ✅ 完成 | 控制命令传输 |

### 2.3 AI 模块 (server/ai/)

| 功能 | 状态 | 说明 |
|------|------|------|
| Whisper ASR | ✅ 完成 | 使用 faster-whisper |
| 流式识别 | ⚠️ 部分 | 基础支持 |
| OpenAI LLM | ✅ 完成 | 支持 GPT 系列 |
| MiniMax LLM | ✅ 完成 | 支持 M2.5 模型 |
| CosyVoice TTS | ✅ 完成 | 支持 SFT/Zero-shot |
| 流式合成 | ✅ 完成 | 支持流式输出 |

### 2.4 核心模块 (server/core/)

| 功能 | 状态 | 说明 |
|------|------|------|
| WebRTC VAD | ✅ 完成 | 语音活动检测 |
| Ring Buffer | ✅ 完成 | 环形缓冲区 |
| Pipeline | ✅ 完成 | 完整处理流水线 |
| 状态管理 | ✅ 完成 | IDLE/CONVERSATION 状态 |
| 唤醒词检测 | ✅ 完成 | 呼叫/退出触发词 |
| 记忆功能 | ✅ 完成 | 长期记忆存储 |

### 2.5 技能模块 (server/skills/)

| 功能 | 状态 | 说明 |
|------|------|------|
| 天气查询 | ✅ 完成 | 使用 wttr.in API |
| 网页总结 | ✅ 完成 | 使用 jina.ai Reader API |
| 技能管理器 | ✅ 完成 | 统一调度入口 |

---

## 三、技术栈

| 组件 | 技术 | 版本/备注 |
|------|------|----------|
| ASR | OpenAI Whisper / faster-whisper | base/model |
| LLM | OpenAI GPT / MiniMax M2.5 | 可配置 |
| TTS | CosyVoice | Fun-CosyVoice3 / CosyVoice-300M |
| VAD | webrtcvad | 4.x |
| WebSocket | websockets | >=12.0 |
| 音频 | pyaudio, numpy | - |
| HTTP | aiohttp | - |

---

## 四、配置说明

### 4.1 必需配置 (.env)

```bash
# LLM 配置 (二选一)
LLM_PROVIDER=minimax          # 或 openai
MINIMAX_API_KEY=your_key      # MiniMax API Key
OPENAI_API_KEY=your_key       # OpenAI API Key

# 可选配置
ASR_MODEL=base                # Whisper 模型大小
COSYVOICE_PATH=./CosyVoice   # CosyVoice 路径
ROBOT_ID_NAME=小智            # 机器人名称
```

### 4.2 唤醒词配置

| 触发词 | 默认值 | 说明 |
|--------|--------|------|
| 呼叫 | 呼叫 | 呼叫前缀 |
| 退出 | 去吧 | 退出前缀 |
| 记忆 | 记住 | 记忆前缀 |

完整触发词示例:
- 呼叫小智 → 进入对谈模式
- 去吧小智 → 退出对谈模式
- 记住今天是小明的生日 → 保存到记忆

---

## 五、启动方式

### 5.1 Python 服务器

```bash
# 激活 conda 环境
conda activate deskbot

# 安装依赖
pip install -r requirements.txt

# 启动服务器
python -m server.main

# 或指定日志级别
python -m server.main debug
```

### 5.2 ESP32 固件

```bash
# 设置 ESP-IDF 环境
. ~/esp/esp-idf/export.sh

# 编译
idf.py build

# 烧录
idf.py -p /dev/ttyUSB0 flash
```

---

## 六、待完成事项

### 6.1 高优先级

- [ ] **ESP32 音频采集与传输** - 固件端音频流处理
- [ ] **ESP32 音频播放** - 接收 TTS 音频并播放
- [ ] **端到端测试** - 完整语音交互流程测试

### 6.2 中优先级

- [ ] **唤醒词优化** - 提升唤醒词检测准确率
- [ ] **流式响应** - LLM 流式输出支持
- [ ] **错误处理** - 完善异常处理和重试机制
- [ ] **测试用例** - 添加单元测试和集成测试

### 6.3 低优先级

- [ ] **日志系统** - 完善日志记录
- [ ] **性能优化** - 延迟优化
- [ ] **多语言支持** - 扩展其他语言
- [ ] **Web UI** - 网页控制界面

---

## 七、已知问题

1. **CosyVoice 模型下载** - 需要手动从 ModelScope/HuggingFace 下载
2. **ESP-IDF 环境** - 需要先配置 ESP-IDF 环境
3. **API Key** - 需要配置有效的 API Key

---

## 八、参考文档

- [CosyVoice GitHub](https://github.com/FunAudioLLM/CosyVoice)
- [ESP-IDF 文档](https://docs.espressif.com/projects/esp-idf/)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [MiniMax API](https://platform.minimaxi.com/)

---

## 九、版本历史

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-02-25 | v0.1.0 | 初始版本完成服务器核心模块 |

---

*本文件由 Claude Code 生成并维护*
