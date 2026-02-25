"""
ASR (Automatic Speech Recognition) module using faster-whisper

Features:
- Fast inference using faster-whisper
- Support for multiple languages
- Streaming and batch processing
"""

import io
import wave
import logging
from typing import Optional, AsyncIterator
import numpy as np

from server.config.settings import config

logger = logging.getLogger(__name__)


class ASR:
    """ASR wrapper using faster-whisper"""

    def __init__(self, asr_config=None):
        """
        Initialize ASR model

        Args:
            asr_config: ASRConfig instance, uses global config if None
        """
        self.asr_config = asr_config or config.asr
        self._model = None
        self._model_loaded = False

        logger.info(
            f"ASR initialized: model={self.asr_config.model}, "
            f"language={self.asr_config.language}, "
            f"device={self.asr_config.device}"
        )

    def _ensure_model_loaded(self):
        """Lazy load the model"""
        if not self._model_loaded:
            try:
                from faster_whisper import WhisperModel

                logger.info(f"Loading Whisper model: {self.asr_config.model}")
                self._model = WhisperModel(
                    self.asr_config.model,
                    device=self.asr_config.device,
                    compute_type=self.asr_config.compute_type
                )
                self._model_loaded = True
                logger.info("Whisper model loaded successfully")
            except ImportError:
                # Fallback to openai-whisper
                logger.warning("faster-whisper not available, falling back to openai-whisper")
                import whisper
                self._model = whisper.load_model(
                    self.asr_config.model,
                    device=self.asr_config.device
                )
                self._model_loaded = True

    async def recognize(self, audio_data: bytes) -> str:
        """
        Recognize speech from audio data

        Args:
            audio_data: Raw PCM audio bytes (16-bit, 16kHz, mono)

        Returns:
            Recognized text
        """
        self._ensure_model_loaded()

        try:
            # Convert bytes to numpy array
            audio_np = self._bytes_to_numpy(audio_data)

            logger.info(f"Recognizing audio: {len(audio_np)} samples")

            # Run recognition
            if hasattr(self._model, 'transcribe'):
                # faster-whisper
                result, info = self._model.transcribe(
                    audio_np,
                    language=self.asr_config.language,
                    beam_size=5,
                    vad_filter=False
                )

                # Get full text
                text = ""
                for segment in result:
                    text += segment.text

                text = text.strip()
                logger.info(f"Recognition result: {text}")
                return text
            else:
                # openai-whisper
                result = self._model.transcribe(
                    audio_np,
                    language=self.asr_config.language
                )
                text = result["text"].strip()
                logger.info(f"Recognition result: {text}")
                return text

        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return ""

    async def recognize_stream(self, audio_chunk: bytes) -> AsyncIterator[str]:
        """
        Stream recognition (for future use with streaming models)

        Args:
            audio_chunk: Audio chunk bytes

        Yields:
            Partial recognition results
        """
        # For now, just yield the final result
        # Streaming VAD + ASR can be added later
        result = await self.recognize(audio_chunk)
        if result:
            yield result

    def _bytes_to_numpy(self, audio_bytes: bytes) -> np.ndarray:
        """
        Convert raw PCM bytes to numpy array

        Args:
            audio_bytes: Raw PCM audio bytes

        Returns:
            numpy array of float32 samples normalized to [-1, 1]
        """
        # Convert to numpy int16
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

        # Convert to float32 and normalize
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        return audio_float32

    def numpy_to_bytes(self, audio_np: np.ndarray) -> bytes:
        """
        Convert numpy array to PCM bytes

        Args:
            audio_np: numpy array of float32 samples in [-1, 1]

        Returns:
            Raw PCM audio bytes
        """
        # Clip to valid range
        audio_np = np.clip(audio_np, -1.0, 1.0)

        # Convert to int16
        audio_int16 = (audio_np * 32767).astype(np.int16)

        # Convert to bytes
        return audio_int16.tobytes()


# Global ASR instance
_asr_instance: Optional[ASR] = None


def get_asr() -> ASR:
    """Get global ASR instance"""
    global _asr_instance
    if _asr_instance is None:
        _asr_instance = ASR()
    return _asr_instance
