"""
TTS (Text-to-Speech) module using CosyVoice

Supports:
- CosyVoice-300M-SFT (SFT mode with preset speakers)
- CosyVoice-300M (zero-shot voice cloning)
- CosyVoice-300M-Instruct (instruction-based)
- Fun-CosyVoice3-0.5B (latest version)
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Optional, List, AsyncIterator
from dataclasses import dataclass

import numpy as np

from server.config.settings import config

logger = logging.getLogger(__name__)


class TTS:
    """TTS wrapper using CosyVoice"""

    def __init__(self, tts_config=None):
        """
        Initialize TTS

        Args:
            tts_config: TTSConfig instance, uses global config if None
        """
        self.tts_config = tts_config or config.tts
        self._model = None
        self._model_loaded = False

        # Get CosyVoice path
        self.cosyvoice_path = Path(self.tts_config.cosyvoice_path)
        if not self.cosyvoice_path.is_absolute():
            # Relative path from project root
            self.cosyvoice_path = Path(__file__).parent.parent.parent / self.tts_config.cosyvoice_path

        logger.info(
            f"TTS initialized: model={self.tts_config.model_name}, "
            f"path={self.cosyvoice_path}"
        )

    def _ensure_model_loaded(self):
        """Lazy load the CosyVoice model"""
        if not self._model_loaded:
            try:
                # Add CosyVoice to path
                import sys
                cosyvoice_third_party = self.cosyvoice_path / "third_party" / "Matcha-TTS"
                if str(cosyvoice_third_party) not in sys.path:
                    sys.path.append(str(cosyvoice_third_party))

                from cosyvoice.cli.cosyvoice import AutoModel

                model_dir = self.cosyvoice_path / "pretrained_models" / self.tts_config.model_name

                if not model_dir.exists():
                    logger.warning(f"Model not found at {model_dir}, using model_dir='{self.tts_config.model_name}'")
                    model_dir = self.tts_config.model_name

                logger.info(f"Loading CosyVoice model from {model_dir}")
                self._model = AutoModel(model_dir=str(model_dir))
                self._model_loaded = True
                logger.info("CosyVoice model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load CosyVoice: {e}")
                raise

    async def synthesize(
        self,
        text: str,
        stream: bool = False
    ) -> bytes:
        """
        Synthesize speech from text

        Args:
            text: Input text
            stream: Enable streaming (not fully supported yet)

        Returns:
            PCM audio bytes
        """
        self._ensure_model_loaded()

        try:
            # Run synthesis in thread pool to avoid blocking
            audio_chunks = await asyncio.to_thread(
                self._synthesize_sync,
                text
            )

            # Concatenate all audio chunks
            audio_data = b''.join(audio_chunks)
            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            raise

    def _synthesize_sync(self, text: str) -> List[bytes]:
        """Synchronous synthesis"""
        audio_chunks = []

        # Check if we have reference audio for zero-shot
        if self.tts_config.ref_audio and self.tts_config.ref_text:
            # Zero-shot mode
            ref_audio = self.tts_config.ref_audio
            ref_text = self.tts_config.ref_text

            for chunk in self._model.inference_zero_shot(text, ref_text, ref_audio):
                audio_np = chunk['tts_speech'].squeeze(0).numpy()
                audio_chunks.append(self._numpy_to_bytes(audio_np))
        else:
            # SFT mode with preset speaker
            # Get available speakers
            speakers = self._model.list_available_spks()
            logger.info(f"Available speakers: {speakers}")

            # Use default Chinese female voice
            speaker = "中文女"
            if speakers:
                # Try to find a Chinese voice
                for s in speakers:
                    if "中文" in s or "Chinese" in s or "zh" in s.lower():
                        speaker = s
                        break

            for chunk in self._model.inference_sft(text, speaker):
                audio_np = chunk['tts_speech'].squeeze(0).numpy()
                audio_chunks.append(self._numpy_to_bytes(audio_np))

        return audio_chunks

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """
        Stream synthesis (yields chunks as they are generated)

        Args:
            text: Input text

        Yields:
            Audio chunks (PCM bytes)
        """
        self._ensure_model_loaded()

        def generate():
            if self.tts_config.ref_audio and self.tts_config.ref_text:
                for chunk in self._model.inference_zero_shot(
                    text,
                    self.tts_config.ref_text,
                    self.tts_config.ref_audio,
                    stream=True
                ):
                    audio_np = chunk['tts_speech'].squeeze(0).numpy()
                    yield self._numpy_to_bytes(audio_np)
            else:
                speaker = "中文女"
                for chunk in self._model.inference_sft(text, speaker, stream=True):
                    audio_np = chunk['tts_speech'].squeeze(0).numpy()
                    yield self._numpy_to_bytes(audio_np)

        for chunk in await asyncio.to_thread(generate):
            yield chunk

    def _numpy_to_bytes(self, audio_np: np.ndarray) -> bytes:
        """
        Convert numpy array to PCM bytes

        Args:
            audio_np: numpy array of float32 samples in [-1, 1]

        Returns:
            Raw PCM audio bytes (16-bit)
        """
        # Clip to valid range
        audio_np = np.clip(audio_np, -1.0, 1.0)

        # Convert to int16
        audio_int16 = (audio_np * 32767).astype(np.int16)

        # Convert to bytes
        return audio_int16.tobytes()

    def get_sample_rate(self) -> int:
        """Get audio sample rate"""
        if self._model_loaded and self._model:
            return self._model.sample_rate
        # Default to 16kHz for CosyVoice
        return 16000


# Global TTS instance
_tts_instance: Optional[TTS] = None


def get_tts() -> TTS:
    """Get global TTS instance"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTS()
    return _tts_instance
