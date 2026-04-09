# AICP Voice

### Speech-to-Text and Text-to-Speech for AI agent voice interaction

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/aicp-ai/aicp)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB)](https://www.python.org/)

---

## Overview

**AICP Voice** provides speech-to-text (STT) and text-to-speech (TTS) capabilities for voice-enabled AI agents. It supports multiple providers with a unified interface, enabling seamless switching between services.

### Features

| Feature | Description |
|---------|-------------|
| **Multi-Provider STT** | Deepgram, OpenAI Whisper, ElevenLabs, local Whisper |
| **Multi-Provider TTS** | OpenAI, ElevenLabs, Coqui, edge-tts |
| **Streaming Transcription** | Real-time audio chunk processing |
| **Voice Client** | Combined STT + TTS interface |
| **Provider Factory** | Easy provider switching |
| **Audio Chunk Streaming** | AsyncIterator-based audio processing |

---

## Installation

```bash
pip install aicp-core
```

---

## Quick Start

### Speech-to-Text

```python
from aicp.voice import (
    VoiceClient,
    STTProvider,
    TTSProvider,
)

client = VoiceClient(
    stt_provider=STTProvider.DEEPGRAM,
    stt_api_key="your-deepgram-key",
    tts_provider=TTSProvider.OPENAI,
    tts_api_key="your-openai-key",
)

await client.connect()

# Listen for voice input
transcript = await client.listen()
if transcript:
    print(f"Transcribed: {transcript}")

# Speak response
await client.speak("Hello, how can I help you?")

await client.close()
```

### STT Client (Direct)

```python
from aicp.voice import (
    VoiceClientFactory,
    STTProvider,
    AudioChunk,
)

# Create STT client
stt = VoiceClientFactory.create_stt_client(
    provider=STTProvider.DEEPGRAM,
    api_key="your-key",
    model="nova-2",
    language="en",
)

await stt.connect()

# Transcribe audio
result = await stt.transcribe(audio_bytes)
print(result.text)

# Stream transcription
async def audio_generator():
    yield AudioChunk(data=chunk1)
    yield AudioChunk(data=chunk2)

async for segment in stt.stream_transcribe(audio_generator()):
    print(f"Segment: {segment.text}")

await stt.close()
```

### TTS Client (Direct)

```python
from aicp.voice import TTSClient, TTSProvider

tts = TTSClient(
    provider=TTSProvider.OPENAI,
    api_key="your-key",
    voice_id="alloy",
)

await tts.connect()

# Synthesize speech
result = await tts.synthesize("Hello world")
# result.audio contains the audio bytes

# Stream synthesis
async for chunk in tts.stream_synthesize("Long text to speak"):
    # Process audio chunks as they arrive
    pass

await tts.close()
```

---

## Supported Providers

### STT Providers

| Provider | Streaming | Languages | Quality |
|----------|-----------|-----------|---------|
| Deepgram | ✅ | 30+ | High |
| OpenAI Whisper | ❌ | 99+ | High |
| ElevenLabs | ✅ | 29+ | Medium |
| Local Whisper | ❌ | 99+ | High |

### TTS Providers

| Provider | Streaming | Voices | Quality |
|----------|-----------|--------|---------|
| OpenAI | ❌ | 6 | High |
| ElevenLabs | ✅ | 100+ | Very High |
| Coqui | ✅ | 100+ | Medium |
| edge-tts | ✅ | 100+ | Medium |

---

## Architecture

### Provider Abstraction

```
VoiceClient
├── STTClient (STTClientBase)
│   ├── DeepgramSTTClient
│   ├── OpenAIWhisperSTTClient
│   └── ...
└── TTSClient
    ├── OpenAI TTS
    ├── ElevenLabs
    └── ...
```

### Data Flow

```
Audio Input → AudioChunk → STT Client → TranscriptSegment → TranscriptionResult
Text Input → TTS Client → AudioChunk → Audio Output
```

---

## API Reference

### VoiceClient

| Method | Description |
|--------|-------------|
| `connect()` | Connect to voice services |
| `listen()` | Listen for voice input and return transcript |
| `speak(text)` | Convert text to speech |
| `is_connected()` | Check connection status |
| `close()` | Close all connections |

### STTClientBase

| Method | Description |
|--------|-------------|
| `connect()` | Establish connection to STT service |
| `transcribe(audio)` | Transcribe complete audio data |
| `stream_transcribe(audio_stream)` | Stream transcription from audio chunks |
| `close()` | Close connection |
| `is_connected()` | Check connection status |

### TTSClient

| Method | Description |
|--------|-------------|
| `connect()` | Initialize TTS service |
| `synthesize(text)` | Convert text to speech |
| `stream_synthesize(text)` | Stream synthesized audio |
| `is_connected()` | Check connection status |
| `close()` | Close connection |

---

## Package Layout

| Module | Purpose |
|--------|---------|
| `stt_client.py` | STT/TTS clients, factory, voice client |
| `__init__.py` | Public API exports |

---

## Development

```bash
# Install for development
git clone https://github.com/aicp-ai/aicp.git
cd aicp/modules/aicp-core
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check .
```

---

## License

Apache 2.0. See `LICENSE`.