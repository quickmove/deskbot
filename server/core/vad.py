"""
Voice Activity Detection (VAD) module using WebRTC VAD

Features:
- Ring Buffer for storing recent audio
- WebRTC VAD for speech detection
- Event-based speech segment detection
"""

import asyncio
import webrtcvad
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional, Deque
import logging

from server.config.settings import config

logger = logging.getLogger(__name__)


@dataclass
class SpeechSegment:
    """Represents a detected speech segment"""
    audio_data: bytes
    start_time: float
    end_time: float


class RingBuffer:
    """Thread-safe ring buffer for audio data"""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self._buffer: Deque[bytes] = deque(maxlen=max_size)
        self._lock = asyncio.Lock()

    async def append(self, data: bytes):
        """Append data to buffer"""
        async with self._lock:
            self._buffer.append(data)

    async def get_all(self) -> bytes:
        """Get all data from buffer as bytes"""
        async with self._lock:
            return b''.join(self._buffer)

    async def get_recent(self, num_bytes: int) -> bytes:
        """Get recent N bytes from buffer"""
        async with self._lock:
            if num_bytes <= 0:
                return b''
            data = b''.join(self._buffer)
            return data[-num_bytes:] if len(data) > num_bytes else data

    async def clear(self):
        """Clear the buffer"""
        async with self._lock:
            self._buffer.clear()

    async def __len__(self):
        async with self._lock:
            return len(self._buffer)


class VAD:
    """Voice Activity Detection using WebRTC VAD"""

    def __init__(self, vad_config=None):
        """
        Initialize VAD

        Args:
            vad_config: VADConfig instance, uses global config if None
        """
        # Use provided config or global config
        self.vad_config = vad_config if vad_config else config.vad
        self.audio_config = config.audio

        # Create VAD instance
        self._vad = webrtcvad.Vad(self.vad_config.aggressiveness)

        # Calculate buffer size
        # ring_buffer_seconds * sample_rate * sample_width * channels
        bytes_per_second = (
            self.audio_config.sample_rate *
            self.audio_config.sample_width *
            self.audio_config.channels
        )
        self._ring_buffer_size = int(self.vad_config.ring_buffer_seconds * bytes_per_second)

        # Create ring buffer
        self._ring_buffer = RingBuffer(max_size=self._ring_buffer_size * 2)

        # State tracking
        self._is_speaking = False
        self._speech_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None

        # Callbacks
        self.on_speech_start: Optional[Callable[[], None]] = None
        self.on_speech_end: Optional[Callable[[bytes], None]] = None
        self.on_vad_update: Optional[Callable[[bool, float], None]] = None

        # Frame size
        self._frame_size = int(
            self.audio_config.sample_rate *
            self.audio_config.sample_width *
            self.audio_config.channels *
            (self.vad_config.frame_duration_ms / 1000)
        )

        logger.info(
            f"VAD initialized: aggressiveness={self.vad_config.aggressiveness}, "
            f"frame_size={self._frame_size} bytes, "
            f"ring_buffer={self._ring_buffer_size} bytes"
        )

    async def process_audio(self, audio_data: bytes, timestamp: float) -> Optional[bytes]:
        """
        Process incoming audio data

        Args:
            audio_data: Raw PCM audio bytes
            timestamp: Current timestamp

        Returns:
            Audio segment if speech ended, None otherwise
        """
        # Add to ring buffer
        await self._ring_buffer.append(audio_data)

        # Check if audio contains speech
        is_speech = self._detect_speech(audio_data)

        if is_speech:
            self._last_speech_time = timestamp

            if not self._is_speaking:
                # Speech started
                self._is_speaking = True
                self._speech_start_time = timestamp
                logger.info(f"Speech started at {timestamp}")
                if self.on_speech_start:
                    self.on_speech_start()

        # Check for speech end
        if self._is_speaking and self._last_speech_time:
            silence_duration = timestamp - self._last_speech_time

            if silence_duration >= (self.vad_config.silence_threshold_ms / 1000.0):
                # Speech ended
                segment_data = await self._ring_buffer.get_all()
                segment = SpeechSegment(
                    audio_data=segment_data,
                    start_time=self._speech_start_time,
                    end_time=timestamp
                )

                logger.info(
                    f"Speech ended at {timestamp}, "
                    f"duration={segment.end_time - segment.start_time:.2f}s"
                )

                # Reset state
                self._is_speaking = False
                self._speech_start_time = None
                self._last_speech_time = None

                # Clear ring buffer
                await self._ring_buffer.clear()

                if self.on_speech_end:
                    self.on_speech_end(segment.audio_data)

                return segment.audio_data

        # Notify VAD update
        if self.on_vad_update:
            self.on_vad_update(is_speaking=is_speech, timestamp=timestamp)

        return None

    def _detect_speech(self, audio_data: bytes) -> bool:
        """
        Detect if audio frame contains speech

        Args:
            audio_data: PCM audio frame

        Returns:
            True if speech detected
        """
        try:
            # Pad or trim to expected frame size
            if len(audio_data) < self._frame_size:
                audio_data = audio_data + b'\x00' * (self._frame_size - len(audio_data))
            elif len(audio_data) > self._frame_size:
                audio_data = audio_data[:self._frame_size]

            # Check with WebRTC VAD
            return self._vad.is_speech(
                audio_data,
                sample_rate=config.audio.sample_rate
            )
        except Exception as e:
            logger.warning(f"VAD detection error: {e}")
            return False

    async def get_recent_audio(self, seconds: float) -> bytes:
        """Get recent N seconds of audio from buffer"""
        bytes_needed = int(
            seconds *
            config.audio.sample_rate *
            config.audio.sample_width *
            config.audio.channels
        )
        return await self._ring_buffer.get_recent(bytes_needed)

    async def get_all_audio(self) -> bytes:
        """Get all audio from buffer"""
        return await self._ring_buffer.get_all()

    async def clear_buffer(self):
        """Clear the ring buffer"""
        await self._ring_buffer.clear()
        self._is_speaking = False
        self._speech_start_time = None
        self._last_speech_time = None

    @property
    def is_speaking(self) -> bool:
        """Check if currently detecting speech"""
        return self._is_speaking
