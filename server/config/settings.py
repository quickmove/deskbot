"""
Configuration management for DeskRobot server
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()


@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = field(default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("SERVER_PORT", "8765")))


@dataclass
class AudioConfig:
    """Audio configuration"""
    sample_rate: int = 16000
    sample_width: int = 2  # 16-bit
    channels: int = 1
    # Buffer settings
    ring_buffer_seconds: float = 10.0  # Keep last 10 seconds of audio


@dataclass
class VADConfig:
    """Voice Activity Detection configuration"""
    # Ring buffer (stored in AudioConfig)
    # ring_buffer_seconds: float = 10.0  # Keep last 10 seconds of audio
    # WebRTC VAD settings
    frame_duration_ms: int = 30  # Frame duration in ms (10, 20, or 30)
    padding_duration_ms: int = 300  # Padding duration in ms
    aggressiveness: int = 2  # 0-3, higher = more aggressive
    # Silence detection
    silence_threshold_ms: int = 700  # ms of silence to end a segment
    min_speech_ms: int = 250  # minimum ms of speech to trigger detection
    # Buffer
    ring_buffer_seconds: float = 10.0  # Keep last 10 seconds of audio


@dataclass
class ASRConfig:
    """ASR (Whisper) configuration"""
    model: str = field(default_factory=lambda: os.getenv("ASR_MODEL", "base"))
    language: str = field(default_factory=lambda: os.getenv("ASR_LANGUAGE", "zh"))
    device: str = "auto"  # auto, cpu, cuda
    # faster-whisper specific
    compute_type: str = "float16"  # float16, int8, float32


@dataclass
class LLMConfig:
    """LLM configuration"""
    # Provider: "openai" or "minimax"
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "minimax"))

    # Common settings
    temperature: float = 0.7
    max_tokens: int = 1024

    # OpenAI settings
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_model: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "gpt-4o-mini"))

    # MiniMax settings (Anthropic compatible)
    minimax_api_key: Optional[str] = field(default_factory=lambda: os.getenv("MINIMAX_API_KEY"))
    minimax_base_url: str = "https://api.minimaxi.com/anthropic"
    minimax_model: str = "MiniMax-M2.5"

    @property
    def api_key(self) -> Optional[str]:
        """Get current provider's API key"""
        if self.provider == "minimax":
            return self.minimax_api_key
        return self.openai_api_key

    @property
    def base_url(self) -> str:
        """Get current provider's base URL"""
        if self.provider == "minimax":
            return self.minimax_base_url
        return self.openai_base_url

    @property
    def model(self) -> str:
        """Get current provider's model name"""
        if self.provider == "minimax":
            return self.minimax_model
        return self.openai_model


@dataclass
class TTSConfig:
    """TTS (CosyVoice) configuration"""
    cosyvoice_path: str = field(default_factory=lambda: os.getenv("COSYVOICE_PATH", "./CosyVoice"))
    model_name: str = field(default_factory=lambda: os.getenv("COSYVOICE_MODEL", "CosyVoice-300M"))
    ref_audio: Optional[str] = field(default_factory=lambda: os.getenv("TTS_REF_AUDIO"))
    ref_text: Optional[str] = field(default_factory=lambda: os.getenv("TTS_REF_TEXT"))
    stream: bool = True  # Enable streaming


@dataclass
class RobotConfig:
    """Robot configuration for voice interaction control"""
    # 机器人名称，用于触发词识别
    id_name: str = field(default_factory=lambda: os.getenv("ROBOT_ID_NAME", "小智"))
    # 触发词配置
    call_trigger: str = "呼叫"  # 呼叫触发词前缀
    exit_trigger: str = "去吧"  # 退出触发词前缀
    # 超时配置（秒）
    conversation_timeout: float = 60.0  # 对谈状态下无语音超时时间
    # 记忆触发词
    remember_trigger: str = "记住"  # 记忆触发词前缀
    # 记忆文件路径（运行时设置）
    memory_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "assets" / "memory")
    memory_file: Path = field(init=False)
    history_file: Path = field(init=False)

    def setup_memory_paths(self):
        """设置记忆文件路径"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"
        # 如果记忆文件不存在，创建空文件
        if not self.memory_file.exists():
            self.memory_file.write_text("# 记忆\n\n")
        if not self.history_file.exists():
            self.history_file.write_text("# 历史\n\n")


@dataclass
class Config:
    """Main configuration container"""
    server: ServerConfig = field(default_factory=ServerConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)

    # Assets directory
    assets_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "assets")
    audio_dir: Path = field(init=False)

    def __post_init__(self):
        """Initialize derived paths"""
        self.audio_dir = self.assets_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        # 初始化记忆目录和文件
        self.robot.setup_memory_paths()

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables"""
        return cls()


# Global config instance
config = Config.from_env()
