#!/usr/bin/env python3
"""
DeskRobot Server Entry Point

启动桌面机器人的 Python 服务器，提供完整的语音交互功能：
- 接收 ESP32 客户端的音频流
- Whisper ASR 语音识别
- OpenAI/MiniMax LLM 对话
- CosyVoice TTS 语音合成

Usage:
    python -m server.main
    或
    python server/main.py
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.config.settings import config


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


async def run_server():
    """Run the WebSocket server"""
    # Import here to avoid import issues
    from server.audio_server import main as server_main

    await server_main()


async def main():
    """Main entry point"""
    logger = logging.getLogger(__name__)

    # Print startup banner
    logger.info("=" * 50)
    logger.info("DeskRobot Server Starting...")
    logger.info("=" * 50)

    # Print configuration
    logger.info(f"Server: {config.server.host}:{config.server.port}")
    logger.info(f"ASR Model: {config.asr.model}, Language: {config.asr.language}")
    logger.info(f"LLM Provider: {config.llm.provider}, Model: {config.llm.model}")
    logger.info(f"TTS Model: {config.tts.model_name}")
    logger.info(f"Robot Name: {config.robot.id_name}")
    logger.info(f"Call Trigger: {config.robot.call_trigger}{config.robot.id_name}")
    logger.info(f"Exit Trigger: {config.robot.exit_trigger}{config.robot.id_name}")

    # Create assets directories
    config.assets_dir.mkdir(parents=True, exist_ok=True)
    config.audio_dir.mkdir(parents=True, exist_ok=True)

    # Run server
    try:
        await run_server()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Get log level from environment
    log_level = sys.argv[1].upper() if len(sys.argv) > 1 else "INFO"
    setup_logging(log_level)

    asyncio.run(main())
