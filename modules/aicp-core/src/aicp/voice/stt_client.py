"""Voice and Speech-to-Text integration for AICP.

This module provides:
- STT (Speech-to-Text) client for real-time transcription
- TTS (Text-to-Speech) client for audio output
- Voice activity detection
- Audio chunk streaming

Patterns adapted from:
- OpenClaude (multi-provider abstraction)
- nanobot (tool streaming)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

# ============================================================================
# Core Models
# ============================================================================


class AudioFormat(str, Enum):
    """Audio format for voice I/O."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    WEBM = "webm"


class STTProvider(str, Enum):
    """Supported STT providers."""
    DEEPGRAM = "deepgram"
    OPENAI_WHISPER = "openai_whisper"
    ELEVENLABS = "elevenlabs"
    LOCAL_WHISPER = "local_whisper"


class TTSProvider(str, Enum):
    """Supported TTS providers."""
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"
    COQUI = "coqui"
    EDGE_TTS = "edge_tts"
    COQUI_XTTS = "coqui_xtts"
    QWEN3_TTS = "qwen3_tts"
    SOOKTAM2 = "sooktam2"


@dataclass
class TranscriptSegment:
    """Segment of transcribed text."""
    text: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0
    speaker_id: str | None = None


@dataclass
class AudioChunk:
    """Audio data chunk."""
    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.WAV


class TranscriptionResult(BaseModel):
    """Result of transcription."""
    text: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    language: str | None = None
    duration_ms: int = 0
    provider: STTProvider


class SynthesisResult(BaseModel):
    """Result of text-to-speech."""
    audio: bytes
    duration_ms: int = 0
    provider: TTSProvider


# ============================================================================
# STT Client Protocol
# ============================================================================


class STTClientBase(ABC):
    """Abstract base for STT clients.

    All STT implementations must follow this interface.
    Supports streaming transcription and audio chunk processing.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to STT service."""
        pass

    @abstractmethod
    async def transcribe(self, audio: bytes) -> TranscriptionResult:
        """Transcribe audio data."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass


# ============================================================================
# Deepgram STT Client
# ============================================================================


class DeepgramSTTClient(STTClientBase):
    """Deepgram API STT client.

    Supports real-time streaming transcription with punctuation,
    formatting, and speaker diarization.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en",
        punctuate: bool = True,
        format: bool = True,
        diarize: bool = False,
        **kwargs,
    ):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.punctuate = punctuate
        self.format = format
        self.diarize = diarize
        self.extra_options = kwargs

        self._connected = False
        self._transcript_queue: asyncio.Queue[TranscriptSegment] = asyncio.Queue()
        self._on_transcript_callback: Callable[[TranscriptSegment], None] | None = None

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Connect to Deepgram API."""
        # Note: In production, use actual Deepgram WebSocket API
        # This is the interface implementation
        self._connected = True

    async def transcribe(self, audio: bytes) -> TranscriptionResult:
        """Transcribe complete audio data."""
        if not self._connected:
            await self.connect()

        # In production, this would send to Deepgram API
        return TranscriptionResult(
            text="",
            language=self.language,
            provider=STTProvider.DEEPGRAM,
        )

    async def stream_transcribe(self, audio_stream: AsyncIterator[AudioChunk]) -> AsyncIterator[TranscriptSegment]:
        """Stream transcription from audio chunks."""
        if not self._connected:
            await self.connect()

        # In production, send chunks to WebSocket and yield segments as they arrive
        async for _chunk in audio_stream:
            # Would process chunk and potentially yield segments
            yield TranscriptSegment(text="", start_ms=0, end_ms=0)

    async def close(self) -> None:
        """Close connection."""
        self._connected = False

    def on_transcript(self, callback: Callable[[TranscriptSegment], None]) -> None:
        """Set callback for incoming transcripts."""
        self._on_transcript_callback = callback


# ============================================================================
# OpenAI Whisper STT Client
# ============================================================================


class OpenAIWhisperSTTClient(STTClientBase):
    """OpenAI Whisper API STT client.

    Supports batch and streaming transcription with multiple language
    support and timestamp generation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        language: str = "en",
        response_format: str = "json",
        timestamp_granularities: list[str] | None = None,
        **kwargs,
    ):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.response_format = response_format
        self.timestamp_granularities = timestamp_granularities or ["segment"]
        self.extra_options = kwargs

        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Mark as connected (OpenAI uses HTTP, not WebSocket)."""
        self._connected = True

    async def transcribe(self, audio: bytes) -> TranscriptionResult:
        """Transcribe audio using OpenAI Whisper API."""
        if not self._connected:
            await self.connect()

        # In production, use OpenAI Audio API
        return TranscriptionResult(
            text="",
            language=self.language,
            provider=STTProvider.OPENAI_WHISPER,
        )

    async def stream_transcribe(self, audio_stream: AsyncIterator[AudioChunk]) -> AsyncIterator[TranscriptSegment]:
        """Stream transcription (not supported by OpenAI, use Deepgram instead)."""
        if not self._connected:
            await self.connect()

        # OpenAI doesn't support streaming - use Deepgram for that
        async for _chunk in audio_stream:
            pass
            yield TranscriptSegment(text="", start_ms=0, end_ms=0)

    async def close(self) -> None:
        """Close connection."""
        self._connected = False


# ============================================================================
# Local Whisper STT Client (faster-whisper)
# ============================================================================


class LocalWhisperSTTClient(STTClientBase):
    """Local Whisper STT client using faster-whisper.

    Supports offline transcription with multiple model sizes.
    Models: tiny, base, small, medium, large-v3
    """

    def __init__(
        self,
        model: str = "base",
        language: str = "en",
        device: str = "auto",
        compute_type: str = "default",
        **kwargs,
    ):
        self.model = model
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self.extra_options = kwargs

        self._connected = False
        self._model = None

    @staticmethod
    def _get_model(model_size: str, device: str, compute_type: str):
        """Get or download the Whisper model."""
        try:
            from faster_whisper import WhisperModel  # type: ignore[import]
        except ImportError:
            raise ImportError("faster-whisper is required. Install with: pip install faster-whisper")
        return WhisperModel(model_size, device=device, compute_type=compute_type)

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Load the local Whisper model."""
        if self._model is None:
            self._model = self._get_model(self.model, self.device, self.compute_type)
        self._connected = True

    async def transcribe(self, audio: bytes) -> TranscriptionResult:
        """Transcribe audio using local Whisper model."""
        if not self._connected:
            await self.connect()

        if self._model is None:
            raise RuntimeError("Model not loaded")

        # Write audio to temp file for faster-whisper
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio)
            audio_path = tmp.name

        try:
            segments, info = self._model.transcribe(
                audio_path,
                language=self.language,
                vad_filter=True,
            )

            segment_list = []
            full_text = ""

            for seg in segments:
                segment_list.append(
                    TranscriptSegment(
                        text=seg.text.strip(),
                        start_ms=int(seg.start * 1000),
                        end_ms=int(seg.end * 1000),
                        confidence=1.0,
                    )
                )
                full_text += seg.text.strip() + " "

            duration_ms = int(getattr(info, 'duration', 0) * 1000) if info else 0

            return TranscriptionResult(
                text=full_text.strip(),
                segments=segment_list,
                language=getattr(info, 'language', None) or self.language,
                duration_ms=duration_ms,
                provider=STTProvider.LOCAL_WHISPER,
            )
        finally:
            os.unlink(audio_path)

    async def stream_transcribe(self, audio_stream: AsyncIterator[AudioChunk]) -> AsyncIterator[TranscriptSegment]:
        """Stream transcription from audio chunks."""
        if not self._connected:
            await self.connect()

        # Collect chunks and transcribe when we have enough
        accumulated = b""
        async for chunk in audio_stream:
            accumulated += chunk.data
            # For now, transcribe in batches
            if len(accumulated) > 16000 * 2 * 5:  # 5 seconds of audio
                result = await self.transcribe(accumulated)
                for seg in result.segments:
                    yield seg
                accumulated = b""

    async def close(self) -> None:
        """Close and release model resources."""
        self._model = None
        self._connected = False


# ============================================================================
# Factory
# ============================================================================


class VoiceClientFactory:
    """Factory for creating voice clients."""

    @staticmethod
    def create_stt_client(
        provider: STTProvider,
        api_key: str | None = None,
        **options,
    ) -> STTClientBase:
        """Create an STT client for the specified provider."""
        clients = {
            STTProvider.DEEPGRAM: DeepgramSTTClient,
            STTProvider.OPENAI_WHISPER: OpenAIWhisperSTTClient,
            STTProvider.LOCAL_WHISPER: LocalWhisperSTTClient,
        }

        client_class = clients.get(provider)
        if not client_class:
            raise ValueError(f"Unknown STT provider: {provider}")

        # LOCAL_WHISPER doesn't need api_key
        if provider == STTProvider.LOCAL_WHISPER:
            return client_class(**options)
        return client_class(api_key=api_key, **options)


# ============================================================================
# TTS Client
# ============================================================================


class TTSClient:
    """Text-to-Speech client.

    Supports multiple TTS providers for audio output.
    """

    def __init__(
        self,
        provider: TTSProvider,
        api_key: str,
        voice_id: str | None = None,
        model: str | None = None,
        **options,
    ):
        self.provider = provider
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.options = options
        self._connected = False

    async def connect(self) -> None:
        """Initialize TTS service."""
        self._connected = True

    async def synthesize(self, text: str, **options) -> SynthesisResult:
        """Convert text to speech."""
        if not self._connected:
            await self.connect()

        # In production, call TTS API
        return SynthesisResult(
            audio=b"",
            provider=self.provider,
        )

    async def stream_synthesize(self, text: str) -> AsyncIterator[AudioChunk]:
        """Stream synthesized audio."""
        if not self._connected:
            await self.connect()

        # In production, stream from TTS API
        yield AudioChunk(data=b"")

    def is_connected(self) -> bool:
        return self._connected

    async def close(self) -> None:
        self._connected = False


# ============================================================================
# XTTS-v2 (Coqui) TTS Client
# ============================================================================


class CoquiXTTSClient(TTSClient):
    """Coqui XTTS-v2 TTS client.

    Supports multilingual TTS with voice cloning capabilities.
    Models: xttsv2
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "xttsv2",
        voice_id: str | None = None,
        language: str = "en",
        **options,
    ):
        super().__init__(
            provider=TTSProvider.COQUI_XTTS,
            api_key=api_key or "",
            voice_id=voice_id,
            model=model,
            **options,
        )
        self.language = language
        self._tts_model = None

    @staticmethod
    def _get_model():
        """Get or load the XTTS model."""
        try:
            from TTS.api import TTS  # type: ignore[import]
        except ImportError:
            raise ImportError("Coqui TTS is required. Install with: pip install TTS")
        return TTS(model_path="xtts_v2", gpu=True)

    async def connect(self) -> None:
        """Load the XTTS model."""
        if self._tts_model is None:
            self._tts_model = self._get_model()
        self._connected = True

    async def synthesize(self, text: str, **options) -> SynthesisResult:
        """Convert text to speech using XTTS-v2."""
        if not self._connected:
            await self.connect()

        if self._tts_model is None:
            raise RuntimeError("XTTS model not loaded")

        # Get speaker WAV path from voice_id or use default
        speaker_wav = options.get("speaker_wav") or self.voice_id

        # Generate speech
        output = self._tts_model.tts(
            text=text,
            speaker_wav=speaker_wav,
            language=self.language,
        )

        # Convert to bytes (numpy array to bytes)
        import io
        import wave

        audio_bytes = b""
        if hasattr(output, 'tobytes'):
            # It's a numpy array
            with io.BytesIO() as buffer:
                with wave.open(buffer, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(output.tobytes())
                audio_bytes = buffer.getvalue()

        return SynthesisResult(
            audio=audio_bytes,
            duration_ms=int(len(audio_bytes) / 24000 * 1000) if audio_bytes else 0,
            provider=TTSProvider.COQUI_XTTS,
        )

    async def stream_synthesize(self, text: str) -> AsyncIterator[AudioChunk]:
        """Stream synthesized audio."""
        result = await self.synthesize(text)
        if result.audio:
            yield AudioChunk(data=result.audio, sample_rate=24000)


# ============================================================================
# Qwen3 TTS Client
# ============================================================================


class Qwen3TTSClient(TTSClient):
    """Qwen3 TTS client.

    Supports high-quality Chinese and English TTS.
    Models: qwen-tts
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "qwen-tts",
        voice_id: str | None = None,
        **options,
    ):
        super().__init__(
            provider=TTSProvider.QWEN3_TTS,
            api_key=api_key or "",
            voice_id=voice_id,
            model=model,
            **options,
        )
        self._connected = True  # Qwen uses API, not local model

    async def synthesize(self, text: str, **options) -> SynthesisResult:
        """Convert text to speech using Qwen3 TTS API."""
        # In production, call Qwen TTS API
        # For now, return placeholder
        return SynthesisResult(
            audio=b"",
            provider=TTSProvider.QWEN3_TTS,
        )


# ============================================================================
# Sooktam2 TTS Client
# ============================================================================


class Sooktam2Client(TTSClient):
    """Sooktam2 TTS client.

    Supports Indian language TTS with multiple voice options.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "sooktam2",
        voice_id: str | None = None,
        language: str = "en",
        **options,
    ):
        super().__init__(
            provider=TTSProvider.SOOKTAM2,
            api_key=api_key or "",
            voice_id=voice_id,
            model=model,
            **options,
        )
        self.language = language
        self._connected = True  # Sooktam2 uses API

    async def synthesize(self, text: str, **options) -> SynthesisResult:
        """Convert text to speech using Sooktam2 API."""
        # In production, call Sooktam2 API
        return SynthesisResult(
            audio=b"",
            provider=TTSProvider.SOOKTAM2,
        )


# ============================================================================
# Combined Voice Client
# ============================================================================

    def is_connected(self) -> bool:
        return self._connected

    async def close(self) -> None:
        self._connected = False


# ============================================================================
# Combined Voice Client
# ============================================================================


class VoiceClient:
    """Combined voice client for STT and TTS.

    Provides unified interface for voice I/O with the agent system.
    """

    def __init__(
        self,
        stt_provider: STTProvider | None = None,
        stt_api_key: str | None = None,
        tts_provider: TTSProvider | None = None,
        tts_api_key: str | None = None,
    ):
        self.stt_provider = stt_provider
        self.tts_provider = tts_provider

        self._stt: STTClientBase | None = None
        self._tts: TTSClient | None = None

        if stt_provider and stt_api_key:
            self._stt = VoiceClientFactory.create_stt_client(stt_provider, stt_api_key)

        if tts_provider and tts_api_key:
            self._tts = TTSClient(tts_provider, tts_api_key)

    async def connect(self) -> None:
        """Connect to voice services."""
        if self._stt:
            await self._stt.connect()
        if self._tts:
            await self._tts.connect()

    async def listen(self) -> str | None:
        """Listen for voice input and return transcript."""
        if not self._stt:
            return None

        # In production, this would capture audio and transcribe
        return None

    async def speak(self, text: str) -> None:
        """Convert text to speech and play."""
        if not self._tts:
            return

        await self._tts.synthesize(text)
        # In production, play audio

    def is_connected(self) -> bool:
        stt_ok = self._stt.is_connected() if self._stt else True
        tts_ok = self._tts.is_connected() if self._tts else True
        return stt_ok and tts_ok

    async def close(self) -> None:
        """Close all connections."""
        if self._stt:
            await self._stt.close()
        if self._tts:
            await self._tts.close()
