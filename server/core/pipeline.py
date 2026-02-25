"""
Audio Processing Pipeline

Integrates VAD + ASR + LLM + TTS for complete voice interaction

Flow:
    Audio Input -> VAD (Voice Detection) -> ASR (Speech Recognition)
    -> LLM (Language Model) -> TTS (Text-to-Speech) -> Output
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Callable, Optional, Awaitable, List
from dataclasses import dataclass, field
from enum import Enum

from server.config.settings import config
from server.core.vad import VAD
from server.ai.asr import ASR
from server.ai.llm import LLM, Message
from server.ai.tts import TTS
from server.skills.manager import get_skill_manager

logger = logging.getLogger(__name__)


# Type alias for callbacks
SpeechCallback = Callable[[str], Awaitable[None]]
LLMCallback = Callable[[str, str], Awaitable[None]]  # (input_text, llm_response)
TTSCallback = Callable[[bytes], Awaitable[None]]  # (audio_data)
VADCallback = Callable[[bool], Awaitable[None]]


class RobotState(Enum):
    """机器人状态枚举"""
    IDLE = "idle"           # 空闲状态
    CONVERSATION = "conversation"  # 对谈状态


@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    enable_llm: bool = True
    enable_tts: bool = True
    # Conversation history
    max_history: int = 10


class AudioPipeline:
    """
    Audio processing pipeline combining VAD, ASR, LLM and TTS

    Complete flow:
    1. VAD detects speech segments
    2. ASR recognizes speech to text
    3. LLM generates response (if enabled)
    4. TTS synthesizes response to audio (if enabled)
    """

    def __init__(self, pipeline_config: Optional[PipelineConfig] = None):
        """Initialize the pipeline"""
        # Initialize components
        self.vad = VAD(config.vad)
        self.asr = ASR(config.asr)
        self.llm = LLM(config.llm)
        self.tts = TTS(config.tts)

        # Pipeline config
        self.pipeline_config = pipeline_config or PipelineConfig()

        # Conversation history
        self.conversation_history: List[Message] = []

        # Callbacks
        self.on_speechrecognized: Optional[SpeechCallback] = None  # ASR result
        self.on_llm_response: Optional[LLMCallback] = None  # LLM response
        self.on_tts_ready: Optional[TTSCallback] = None  # TTS audio ready
        self.on_vad_update: Optional[VADCallback] = None

        # State
        self._running = False
        self._processing = False

        # Robot state management
        self.state = RobotState.IDLE
        self.last_speech_time: Optional[float] = None  # 上次检测到语音的时间

        # Skills
        self.skill_manager = get_skill_manager()

        # Setup VAD callbacks
        self.vad.on_speech_end = self._handle_speech_end

        logger.info("AudioPipeline initialized")
        logger.info(f"  LLM enabled: {self.pipeline_config.enable_llm}")
        logger.info(f"  TTS enabled: {self.pipeline_config.enable_tts}")

    async def start(self):
        """Start the pipeline"""
        self._running = True
        logger.info("AudioPipeline started")

    async def stop(self):
        """Stop the pipeline"""
        self._running = False
        await self.vad.clear_buffer()
        # Reset state
        self.state = RobotState.IDLE
        self.last_speech_time = None
        logger.info("AudioPipeline stopped")

    def _check_call_trigger(self, text: str) -> bool:
        """检查是否是呼叫触发词"""
        call_phrase = f"{config.robot.call_trigger}{config.robot.id_name}"
        return call_phrase in text

    def _check_exit_trigger(self, text: str) -> bool:
        """检查是否是退出触发词"""
        exit_phrase = f"{config.robot.exit_trigger}{config.robot.id_name}"
        return exit_phrase in text

    def _check_timeout(self) -> bool:
        """检查是否超时"""
        if self.last_speech_time is None:
            return False
        elapsed = time.time() - self.last_speech_time
        return elapsed > config.robot.conversation_timeout

    def _transition_to_conversation(self):
        """转入对谈状态"""
        if self.state != RobotState.CONVERSATION:
            self.state = RobotState.CONVERSATION
            self.last_speech_time = time.time()
            logger.info(f"Robot state: IDLE -> CONVERSATION (triggered by call)")

    def _transition_to_idle(self, reason: str = ""):
        """转入空闲状态"""
        if self.state != RobotState.IDLE:
            self.state = RobotState.IDLE
            self.last_speech_time = None
            self.conversation_history.clear()  # 清除对话历史
            logger.info(f"Robot state: CONVERSATION -> IDLE ({reason})")

    def _load_memory(self) -> str:
        """加载长期记忆"""
        try:
            memory_file = config.robot.memory_file
            if memory_file.exists():
                content = memory_file.read_text(encoding='utf-8')
                # 跳过标题行
                lines = content.split('\n')
                if lines and lines[0].startswith('#'):
                    return '\n'.join(lines[1:]).strip()
                return content.strip()
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
        return ""

    def _save_to_memory(self, text: str) -> bool:
        """保存内容到记忆文件"""
        try:
            memory_file = config.robot.memory_file
            # 提取要记住的内容（去掉"记住"触发词）
            content = text
            for trigger in [config.robot.remember_trigger, "记住"]:
                if content.startswith(trigger):
                    content = content[len(trigger):].strip()
                    break

            if not content:
                return False

            # 追加到记忆文件
            with open(memory_file, 'a', encoding='utf-8') as f:
                f.write(f"- {content}\n")

            logger.info(f"Saved to memory: {content}")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False

    def _check_remember_trigger(self, text: str) -> bool:
        """检查是否是记忆触发词"""
        return text.startswith(config.robot.remember_trigger) or text.startswith("记住")

    async def process_audio(self, audio_data: bytes) -> Optional[dict]:
        """
        Process incoming audio data through the pipeline

        Args:
            audio_data: Raw PCM audio bytes

        Returns:
            Dictionary with results:
            {
                "text": str,  # recognized text
                "llm_response": str,  # LLM response (if enabled)
                "tts_audio": bytes,  # TTS audio (if enabled)
            }
        """
        if not self._running:
            return None

        timestamp = time.time()

        # Process through VAD
        result = await self.vad.process_audio(audio_data, timestamp)

        # If VAD detected end of speech, recognize it
        if result:
            return await self._process_full_pipeline(result)

        return None

    async def _handle_speech_end(self, audio_data: bytes):
        """
        Callback when VAD detects speech end

        Args:
            audio_data: Audio segment data
        """
        if self._processing:
            logger.warning("Previous recognition still processing, skipping")
            return

        self._processing = True
        try:
            # Process through full pipeline
            result = await self._process_full_pipeline(audio_data)

            if result:
                # Notify callbacks
                if self.on_speechrecognized and result.get("text"):
                    await self.on_speechrecognized(result["text"])

                if self.on_llm_response and result.get("llm_response"):
                    await self.on_llm_response(result["text"], result["llm_response"])

                if self.on_tts_ready and result.get("tts_audio"):
                    await self.on_tts_ready(result["tts_audio"])
        finally:
            self._processing = False

    async def _process_full_pipeline(self, audio_data: bytes) -> dict:
        """
        Process audio through the complete pipeline

        Args:
            audio_data: Audio bytes

        Returns:
            Dictionary with all results
        """
        result = {
            "text": "",
            "llm_response": "",
            "tts_audio": None,
            "state_change": None
        }

        # Step 1: ASR - Recognize speech to text
        try:
            logger.info(f"ASR: Recognizing {len(audio_data)} bytes of audio")
            text = await self.asr.recognize(audio_data)
            if not text:
                logger.warning("ASR: No text recognized")
                return result
            result["text"] = text
            logger.info(f"ASR: Recognized '{text}'")
        except Exception as e:
            logger.error(f"ASR error: {e}")
            return result

        # Step 1.5: State management - handle state transitions based on recognized text
        current_time = time.time()

        if self.state == RobotState.IDLE:
            # IDLE 状态下检查呼叫触发词
            if self._check_call_trigger(text):
                self._transition_to_conversation()
                result["state_change"] = "enter_conversation"
                logger.info(f"Entered conversation mode")
                # 呼叫成功，不返回 LLM 响应，让用户继续说话
                return result
            else:
                # IDLE 状态下收到非呼叫触发词，不处理
                logger.info(f"IDLE state: ignoring '{text}' (not a call trigger)")
                result["ignored"] = True
                return result

        elif self.state == RobotState.CONVERSATION:
            # 更新最后语音时间
            self.last_speech_time = current_time

            # 检查退出触发词
            if self._check_exit_trigger(text):
                self._transition_to_idle("exit trigger")
                result["state_change"] = "exit_conversation"
                logger.info(f"Exited conversation mode")
                return result

            # 检查超时
            if self._check_timeout():
                self._transition_to_idle("timeout")
                result["state_change"] = "timeout"
                logger.info(f"Conversation timed out")
                return result

            # 检查记忆触发词
            if self._check_remember_trigger(text):
                if self._save_to_memory(text):
                    result["llm_response"] = "好的，我记住了。"
                    logger.info("Memory saved")
                else:
                    result["llm_response"] = "抱歉，保存记忆失败了。"
                return result

        # Step 1.8: Skill - Check if user is invoking a skill (weather, summarize, etc.)
        if self.state == RobotState.CONVERSATION and self.pipeline_config.enable_llm:
            skill_response = await self.skill_manager.handle_skill(text)
            if skill_response:
                result["llm_response"] = skill_response
                logger.info(f"Skill response: {skill_response}")
                return result

        # Step 2: LLM - Generate response (only in CONVERSATION state)
        if self.pipeline_config.enable_llm and self.state == RobotState.CONVERSATION:
            try:
                llm_response = await self._generate_llm_response(text)
                result["llm_response"] = llm_response
                logger.info(f"LLM: Response '{llm_response}'")
            except Exception as e:
                logger.error(f"LLM error: {e}")
                result["llm_response"] = "抱歉，我遇到了问题。"

        # Step 3: TTS - Synthesize speech
        if self.pipeline_config.enable_tts and result["llm_response"]:
            try:
                tts_audio = await self.tts.synthesize(result["llm_response"])
                result["tts_audio"] = tts_audio
                logger.info(f"TTS: Generated {len(tts_audio)} bytes of audio")
            except Exception as e:
                logger.error(f"TTS error: {e}")

        return result

    async def _generate_llm_response(self, user_text: str) -> str:
        """
        Generate LLM response

        Args:
            user_text: User input text

        Returns:
            LLM response text
        """
        # Add user message to history
        self.conversation_history.append(Message(role="user", content=user_text))

        # Trim history if too long
        max_history = self.pipeline_config.max_history
        if len(self.conversation_history) > max_history:
            # Keep system prompt if exists, and last max_history messages
            if self.conversation_history and self.conversation_history[0].role == "system":
                self.conversation_history = (
                    [self.conversation_history[0]] +
                    self.conversation_history[-(max_history):]
                )
            else:
                self.conversation_history = self.conversation_history[-max_history:]

        # System prompt
        memory = self._load_memory()
        if memory:
            system_prompt = f"""你是一个友好的语音助手，请用简短的中文回答用户的问题。

# 记忆
{memory}
"""
        else:
            system_prompt = "你是一个友好的语音助手，请用简短的中文回答用户的问题。"

        # Get LLM response
        response = await self.llm.chat(
            messages=self.conversation_history,
            system=system_prompt
        )

        # Add assistant response to history
        self.conversation_history.append(Message(role="assistant", content=response.content))

        return response.content

    async def chat(self, text: str) -> str:
        """
        Send text to LLM directly (for testing)

        Args:
            text: Input text

        Returns:
            LLM response
        """
        return await self._generate_llm_response(text)

    async def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    async def get_vad_status(self) -> dict:
        """Get current VAD status"""
        return {
            "is_speaking": self.vad.is_speaking
        }

    def get_robot_state(self) -> dict:
        """Get current robot state"""
        return {
            "state": self.state.value,
            "last_speech_time": self.last_speech_time,
            "id_name": config.robot.id_name
        }


# Global pipeline instance
_pipeline: Optional[AudioPipeline] = None


def get_pipeline() -> AudioPipeline:
    """Get global pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = AudioPipeline()
    return _pipeline
