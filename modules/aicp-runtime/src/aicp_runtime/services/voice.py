import base64
import io
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class VoiceOperation(str, Enum):
    TRANSCRIBE = "transcribe"
    SYNTHESIZE = "synthesize"
    STREAM = "stream"


class VoiceProvider(str, Enum):
    DEEPGRAM = "deepgram"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    LOCAL = "local"


class VoiceError(AicpError):
    pass


class VoiceProviderError(VoiceError):
    pass


class VoiceNotSupportedError(VoiceError):
    pass


@dataclass
class VoiceTranscriptionResult:
    text: str
    confidence: float
    duration_ms: int
    language: str
    words: list[dict[str, Any]]


@dataclass
class VoiceSynthesisResult:
    audio_data: bytes
    duration_ms: int
    format: str


class VoiceConfig(BaseModel):
    operation: VoiceOperation
    audio_data: Optional[str] = None
    text: Optional[str] = None
    voice_id: str = Field(default="default")
    provider: VoiceProvider = Field(default=VoiceProvider.DEEPGRAM)
    language: str = Field(default="en")
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)


class VoiceService:
    def __init__(self):
        self._api_keys: dict[VoiceProvider, str] = {}
        self._base_urls: dict[VoiceProvider, str] = {}
        self._deepgram_client: Any = None
        self._elevenlabs_client: Any = None
        self._openai_client: Any = None

    def configure_provider(
        self, provider: VoiceProvider, api_key: str, base_url: Optional[str] = None
    ) -> None:
        self._api_keys[provider] = api_key
        if base_url:
            self._base_urls[provider] = base_url

    def _get_api_key(self, provider: VoiceProvider) -> Optional[str]:
        return self._api_keys.get(provider)

    def _get_base_url(self, provider: VoiceProvider) -> Optional[str]:
        return self._base_urls.get(provider)

    async def transcribe(
        self,
        audio_data: bytes,
        provider: VoiceProvider = VoiceProvider.DEEPGRAM,
        language: str = "en",
    ) -> VoiceTranscriptionResult:
        if provider == VoiceProvider.LOCAL:
            return await self._transcribe_local(audio_data, language)
        if provider == VoiceProvider.DEEPGRAM:
            return await self._transcribe_deepgram(audio_data, language)
        if provider == VoiceProvider.OPENAI:
            return await self._transcribe_openai(audio_data, language)
        raise VoiceNotSupportedError(f"Transcription not supported for {provider}")

    async def synthesize(
        self,
        text: str,
        provider: VoiceProvider = VoiceProvider.OPENAI,
        voice_id: str = "default",
        language: str = "en",
    ) -> VoiceSynthesisResult:
        if provider == VoiceProvider.LOCAL:
            return await self._synthesize_local(text, voice_id)
        if provider == VoiceProvider.OPENAI:
            return await self._synthesize_openai(text, voice_id)
        if provider == VoiceProvider.ELEVENLABS:
            return await self._synthesize_elevenlabs(text, voice_id)
        raise VoiceNotSupportedError(f"Synthesis not supported for {provider}")

    async def _transcribe_local(
        self, audio_data: bytes, language: str
    ) -> VoiceTranscriptionResult:
        raise VoiceNotSupportedError(
            "Local transcription requires whisper or faster-whisper installed"
        )

    async def _transcribe_deepgram(
        self, audio_data: bytes, language: str
    ) -> VoiceTranscriptionResult:
        api_key = self._get_api_key(VoiceProvider.DEEPGRAM)
        if not api_key:
            raise VoiceProviderError("Deepgram API key not configured")
        try:
            from deepgram import DeepgramClient, PrerecordedOptions

            client = DeepgramClient(api_key)
            payload = {"buffer": audio_data}
            options = PrerecordedOptions(
                model="nova-2",
                language=language,
                smart_format=True,
            )
            response = client.listen.prerecorded.v("1").transcribe_file(
                payload, options
            )
            result = response.results.channels[0].alternatives[0]
            return VoiceTranscriptionResult(
                text=result.transcript,
                confidence=result.confidence or 0.0,
                duration_ms=int(response.results.channels[0].audio_duration * 1000),
                language=language,
                words=[
                    {"word": w.word, "start": w.start, "end": w.end}
                    for w in result.words
                ],
            )
        except ImportError:
            raise VoiceProviderError("deepgram-sdk not installed")
        except Exception as e:
            raise VoiceProviderError(f"Deepgram transcription failed: {e}")

    async def _transcribe_openai(
        self, audio_data: bytes, language: str
    ) -> VoiceTranscriptionResult:
        api_key = self._get_api_key(VoiceProvider.OPENAI)
        if not api_key:
            raise VoiceProviderError("OpenAI API key not configured")
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key, base_url=self._get_base_url(VoiceProvider.OPENAI)
            )
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
            )
            return VoiceTranscriptionResult(
                text=response.text,
                confidence=0.95,
                duration_ms=0,
                language=language,
                words=[],
            )
        except ImportError:
            raise VoiceProviderError("openai not installed")
        except Exception as e:
            raise VoiceProviderError(f"OpenAI transcription failed: {e}")

    async def _synthesize_local(self, text: str, voice_id: str) -> VoiceSynthesisResult:
        raise VoiceNotSupportedError(
            "Local synthesis requires pyttsx3 or similar installed"
        )

    async def _synthesize_openai(
        self, text: str, voice_id: str
    ) -> VoiceSynthesisResult:
        api_key = self._get_api_key(VoiceProvider.OPENAI)
        if not api_key:
            raise VoiceProviderError("OpenAI API key not configured")
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key, base_url=self._get_base_url(VoiceProvider.OPENAI)
            )
            voice = (
                voice_id
                if voice_id in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                else "alloy"
            )
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
            )
            audio_data = response.content
            duration_ms = len(text) * 80
            return VoiceSynthesisResult(
                audio_data=audio_data,
                duration_ms=duration_ms,
                format="mp3",
            )
        except ImportError:
            raise VoiceProviderError("openai not installed")
        except Exception as e:
            raise VoiceProviderError(f"OpenAI synthesis failed: {e}")

    async def _synthesize_elevenlabs(
        self, text: str, voice_id: str
    ) -> VoiceSynthesisResult:
        api_key = self._get_api_key(VoiceProvider.ELEVENLABS)
        if not api_key:
            raise VoiceProviderError("ElevenLabs API key not configured")
        try:
            from elevenlabs import ElevenLabs

            client = ElevenLabs(api_key=api_key)
            voice = voice_id if voice_id != "default" else "EXAVITQu4vr4xnSDxMaL"
            audio_iterator = client.generate(text=text, voice=voice)
            audio_data = b"".join(audio_iterator)
            duration_ms = len(text) * 80
            return VoiceSynthesisResult(
                audio_data=audio_data,
                duration_ms=duration_ms,
                format="mp3",
            )
        except ImportError:
            raise VoiceProviderError("elevenlabs not installed")
        except Exception as e:
            raise VoiceProviderError(f"ElevenLabs synthesis failed: {e}")

    async def process_config(self, config: VoiceConfig) -> dict[str, Any]:
        if config.operation == VoiceOperation.TRANSCRIBE:
            if not config.audio_data:
                raise VoiceError("audio_data required for transcription")
            audio_bytes = base64.b64decode(config.audio_data)
            result = await self.transcribe(
                audio_bytes,
                provider=config.provider,
                language=config.language,
            )
            return {
                "text": result.text,
                "confidence": result.confidence,
                "duration_ms": result.duration_ms,
                "language": result.language,
                "words": result.words,
            }
        if config.operation == VoiceOperation.SYNTHESIZE:
            if not config.text:
                raise VoiceError("text required for synthesis")
            result = await self.synthesize(
                config.text,
                provider=config.provider,
                voice_id=config.voice_id,
                language=config.language,
            )
            return {
                "audio_data": base64.b64encode(result.audio_data).decode(),
                "duration_ms": result.duration_ms,
                "format": result.format,
            }
        raise VoiceNotSupportedError(f"Operation {config.operation} not supported")

    async def stream_synthesis(
        self,
        text_stream,
        provider: VoiceProvider = VoiceProvider.OPENAI,
        voice_id: str = "default",
    ):
        if provider == VoiceProvider.OPENAI:
            async for chunk in self._stream_synthesis_openai(text_stream, voice_id):
                yield chunk
        elif provider == VoiceProvider.ELEVENLABS:
            async for chunk in self._stream_synthesis_elevenlabs(text_stream, voice_id):
                yield chunk
        else:
            raise VoiceNotSupportedError(f"Streaming not supported for {provider}")

    async def _stream_synthesis_openai(self, text_stream, voice_id: str):
        api_key = self._get_api_key(VoiceProvider.OPENAI)
        if not api_key:
            raise VoiceProviderError("OpenAI API key not configured")
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key, base_url=self._get_base_url(VoiceProvider.OPENAI)
            )
            voice = (
                voice_id
                if voice_id in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                else "alloy"
            )
            buffer = ""
            async for text in text_stream:
                buffer += text
                if len(buffer) > 100:
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice=voice,
                        input=buffer,
                    )
                    yield response.content
                    buffer = ""
            if buffer:
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=buffer,
                )
                yield response.content
        except ImportError:
            raise VoiceProviderError("openai not installed")
        except Exception as e:
            raise VoiceProviderError(f"OpenAI streaming synthesis failed: {e}")

    async def _stream_synthesis_elevenlabs(self, text_stream, voice_id: str):
        api_key = self._get_api_key(VoiceProvider.ELEVENLABS)
        if not api_key:
            raise VoiceProviderError("ElevenLabs API key not configured")
        try:
            from elevenlabs import ElevenLabs

            client = ElevenLabs(api_key=api_key)
            voice = voice_id if voice_id != "default" else "EXAVITQu4vr4xnSDxMaL"
            buffer = ""
            async for text in text_stream:
                buffer += text
                if len(buffer) > 100:
                    audio_iterator = client.generate(
                        text=buffer, voice=voice, stream=True
                    )
                    for chunk in audio_iterator:
                        yield chunk
                    buffer = ""
            if buffer:
                audio_iterator = client.generate(text=buffer, voice=voice, stream=True)
                for chunk in audio_iterator:
                    yield chunk
        except ImportError:
            raise VoiceProviderError("elevenlabs not installed")
        except Exception as e:
            raise VoiceProviderError(f"ElevenLabs streaming synthesis failed: {e}")
