from __future__ import annotations

from types import SimpleNamespace

import pytest

from aicp.voice.stt_client import (
    LocalWhisperSTTClient,
    STTProvider,
    TranscriptSegment,
    VoiceClientFactory,
)


class _FakeSegment:
    def __init__(self, text: str, start: float, end: float) -> None:
        self.text = text
        self.start = start
        self.end = end


class _FakeWhisperModel:
    def __init__(self, model_size: str, device: str, compute_type: str) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.calls: list[str] = []

    def transcribe(self, audio_path: str, language: str | None = None, vad_filter: bool = True):
        self.calls.append(audio_path)
        segments = [
            _FakeSegment(" hello", 0.0, 0.5),
            _FakeSegment(" world ", 0.5, 1.25),
        ]
        info = SimpleNamespace(language=language or "en", duration=1.25)
        return iter(segments), info


class TestLocalWhisperSTTClient:
    @pytest.mark.asyncio
    async def test_transcribe_returns_transcription_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, _FakeWhisperModel] = {}

        def fake_get_model(model_size: str, device: str, compute_type: str) -> _FakeWhisperModel:
            model = _FakeWhisperModel(model_size, device, compute_type)
            captured["model"] = model
            return model

        monkeypatch.setattr(LocalWhisperSTTClient, "_get_model", staticmethod(fake_get_model))

        client = LocalWhisperSTTClient(model="base", language="en", compute_type="int8")
        result = await client.transcribe(b"fake wav bytes")

        assert result.text == "hello world"
        assert result.language == "en"
        assert result.provider == STTProvider.LOCAL_WHISPER
        assert result.duration_ms == 1250
        assert result.segments == [
            TranscriptSegment(text="hello", start_ms=0, end_ms=500),
            TranscriptSegment(text="world", start_ms=500, end_ms=1250),
        ]
        assert client.is_connected() is True
        assert captured["model"].model_size == "base"
        assert captured["model"].compute_type == "int8"
        assert len(captured["model"].calls) == 1

    @pytest.mark.asyncio
    async def test_close_marks_client_disconnected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            LocalWhisperSTTClient,
            "_get_model",
            staticmethod(lambda model_size, device, compute_type: _FakeWhisperModel(model_size, device, compute_type)),
        )

        client = LocalWhisperSTTClient(model="tiny")
        await client.connect()
        assert client.is_connected() is True

        await client.close()

        assert client.is_connected() is False

    def test_factory_creates_local_whisper_client(self) -> None:
        client = VoiceClientFactory.create_stt_client(
            provider=STTProvider.LOCAL_WHISPER,
            api_key="",
            model="small",
        )

        assert isinstance(client, LocalWhisperSTTClient)
