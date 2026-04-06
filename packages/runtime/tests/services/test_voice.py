import base64

import pytest
from aicp_runtime.services.voice import (
    VoiceConfig,
    VoiceError,
    VoiceNotSupportedError,
    VoiceOperation,
    VoiceProvider,
    VoiceProviderError,
    VoiceService,
    VoiceSynthesisResult,
    VoiceTranscriptionResult,
)


class TestVoiceConfig:
    def test_default_config(self):
        config = VoiceConfig(operation=VoiceOperation.TRANSCRIBE)
        assert config.operation == VoiceOperation.TRANSCRIBE
        assert config.provider == VoiceProvider.DEEPGRAM
        assert config.language == "en"
        assert config.voice_id == "default"

    def test_custom_config(self):
        config = VoiceConfig(
            operation=VoiceOperation.SYNTHESIZE,
            text="Hello world",
            voice_id="nova",
            provider=VoiceProvider.OPENAI,
            language="es",
        )
        assert config.operation == VoiceOperation.SYNTHESIZE
        assert config.text == "Hello world"
        assert config.voice_id == "nova"
        assert config.provider == VoiceProvider.OPENAI
        assert config.language == "es"


class TestVoiceEnums:
    def test_operation_values(self):
        assert VoiceOperation.TRANSCRIBE == "transcribe"
        assert VoiceOperation.SYNTHESIZE == "synthesize"
        assert VoiceOperation.STREAM == "stream"

    def test_provider_values(self):
        assert VoiceProvider.DEEPGRAM == "deepgram"
        assert VoiceProvider.ELEVENLABS == "elevenlabs"
        assert VoiceProvider.OPENAI == "openai"
        assert VoiceProvider.LOCAL == "local"


class TestVoiceServiceConfiguration:
    def test_init(self):
        service = VoiceService()
        assert len(service._api_keys) == 0
        assert len(service._base_urls) == 0

    def test_configure_provider_api_key(self):
        service = VoiceService()
        service.configure_provider(VoiceProvider.OPENAI, "test-key-123")
        assert service._get_api_key(VoiceProvider.OPENAI) == "test-key-123"

    def test_configure_provider_with_base_url(self):
        service = VoiceService()
        service.configure_provider(
            VoiceProvider.OPENAI, "test-key", base_url="https://api.example.com"
        )
        assert service._get_api_key(VoiceProvider.OPENAI) == "test-key"
        assert service._get_base_url(VoiceProvider.OPENAI) == "https://api.example.com"


class TestVoiceTranscriptionResult:
    def test_creation(self):
        result = VoiceTranscriptionResult(
            text="Hello world",
            confidence=0.95,
            duration_ms=1234,
            language="en",
            words=[{"word": "Hello", "start": 0.0, "end": 0.5}],
        )
        assert result.text == "Hello world"
        assert result.confidence == 0.95
        assert result.duration_ms == 1234
        assert len(result.words) == 1


class TestVoiceSynthesisResult:
    def test_creation(self):
        result = VoiceSynthesisResult(
            audio_data=b"fake audio data",
            duration_ms=2345,
            format="mp3",
        )
        assert result.audio_data == b"fake audio data"
        assert result.duration_ms == 2345
        assert result.format == "mp3"


@pytest.mark.asyncio
class TestVoiceServiceTranscription:
    async def test_local_transcription_not_supported(self):
        service = VoiceService()
        with pytest.raises(VoiceNotSupportedError):
            await service.transcribe(b"audio", provider=VoiceProvider.LOCAL)

    async def test_deepgram_requires_api_key(self):
        service = VoiceService()
        with pytest.raises(VoiceProviderError):
            await service.transcribe(b"audio", provider=VoiceProvider.DEEPGRAM)

    async def test_openai_requires_api_key(self):
        service = VoiceService()
        with pytest.raises(VoiceProviderError):
            await service.transcribe(b"audio", provider=VoiceProvider.OPENAI)


@pytest.mark.asyncio
class TestVoiceServiceSynthesis:
    async def test_local_synthesis_not_supported(self):
        service = VoiceService()
        with pytest.raises(VoiceNotSupportedError):
            await service.synthesize("Hello", provider=VoiceProvider.LOCAL)

    async def test_openai_requires_api_key(self):
        service = VoiceService()
        with pytest.raises(VoiceProviderError):
            await service.synthesize("Hello", provider=VoiceProvider.OPENAI)

    async def test_elevenlabs_requires_api_key(self):
        service = VoiceService()
        with pytest.raises(VoiceProviderError):
            await service.synthesize("Hello", provider=VoiceProvider.ELEVENLABS)


@pytest.mark.asyncio
class TestVoiceServiceProcessConfig:
    async def test_transcribe_requires_audio_data(self):
        service = VoiceService()
        config = VoiceConfig(operation=VoiceOperation.TRANSCRIBE)
        with pytest.raises(VoiceError):
            await service.process_config(config)

    async def test_synthesize_requires_text(self):
        service = VoiceService()
        config = VoiceConfig(operation=VoiceOperation.SYNTHESIZE)
        with pytest.raises(VoiceError):
            await service.process_config(config)

    async def test_unsupported_operation(self):
        service = VoiceService()
        config = VoiceConfig(operation=VoiceOperation.STREAM)
        with pytest.raises(VoiceNotSupportedError):
            await service.process_config(config)


class TestVoiceErrors:
    def test_voice_error_is_aicp_error(self):
        from aicp.errors import AicpError

        assert issubclass(VoiceError, AicpError)

    def test_voice_provider_error_is_voice_error(self):
        assert issubclass(VoiceProviderError, VoiceError)

    def test_voice_not_supported_error_is_voice_error(self):
        assert issubclass(VoiceNotSupportedError, VoiceError)
