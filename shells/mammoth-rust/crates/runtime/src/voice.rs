use anyhow::{anyhow, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WhisperBackend {
    OpenAI,
    Local,
}

impl WhisperBackend {
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "openai" => Some(Self::OpenAI),
            "local" => Some(Self::Local),
            _ => None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct VoiceInputConfig {
    pub sample_rate: u32,
    pub channels: u16,
    pub backend: WhisperBackend,
    pub vad_enabled: bool,
    pub vad_silence_threshold_ms: u64,
}

impl Default for VoiceInputConfig {
    fn default() -> Self {
        Self {
            sample_rate: 16_000,
            channels: 1,
            backend: WhisperBackend::OpenAI,
            vad_enabled: true,
            vad_silence_threshold_ms: 500,
        }
    }
}

pub struct VoiceInput {
    pub config: VoiceInputConfig,
}

impl VoiceInput {
    #[must_use]
    pub fn new(config: VoiceInputConfig) -> Self {
        Self { config }
    }

    #[must_use]
    pub fn encode_wav_header(sample_rate: u32, channels: u16, num_samples: u32) -> Vec<u8> {
        let byte_rate = sample_rate * u32::from(channels) * 2;
        let data_size = num_samples * u32::from(channels) * 2;
        let mut h = Vec::with_capacity(44);
        h.extend_from_slice(b"RIFF");
        h.extend_from_slice(&(36 + data_size).to_le_bytes());
        h.extend_from_slice(b"WAVE");
        h.extend_from_slice(b"fmt ");
        h.extend_from_slice(&16u32.to_le_bytes());
        h.extend_from_slice(&1u16.to_le_bytes());
        h.extend_from_slice(&channels.to_le_bytes());
        h.extend_from_slice(&sample_rate.to_le_bytes());
        h.extend_from_slice(&byte_rate.to_le_bytes());
        h.extend_from_slice(&(channels * 2).to_le_bytes());
        h.extend_from_slice(&16u16.to_le_bytes());
        h.extend_from_slice(b"data");
        h.extend_from_slice(&data_size.to_le_bytes());
        h
    }

    pub async fn record(&self, max_duration_secs: f32) -> Result<Vec<i16>> {
        let _ = max_duration_secs;
        Ok(Vec::new())
    }

    pub async fn transcribe(&self, samples: Vec<i16>) -> Result<String> {
        let mut wav_data =
            Self::encode_wav_header(self.config.sample_rate, self.config.channels, samples.len() as u32);
        for sample in &samples {
            wav_data.extend_from_slice(&sample.to_le_bytes());
        }

        match self.config.backend {
            WhisperBackend::OpenAI => self.transcribe_openai(wav_data).await,
            WhisperBackend::Local => self.transcribe_local(wav_data).await,
        }
    }

    async fn transcribe_openai(&self, wav_bytes: Vec<u8>) -> Result<String> {
        let api_key = std::env::var("OPENAI_API_KEY").map_err(|_| anyhow!("OPENAI_API_KEY not set"))?;
        let client = reqwest::Client::new();
        let part = reqwest::multipart::Part::bytes(wav_bytes)
            .file_name("audio.wav")
            .mime_str("audio/wav")?;
        let form = reqwest::multipart::Form::new()
            .part("file", part)
            .text("model", "whisper-1");
        let resp: serde_json::Value = client
            .post("https://api.openai.com/v1/audio/transcriptions")
            .bearer_auth(api_key)
            .multipart(form)
            .send()
            .await?
            .json()
            .await?;
        Ok(resp["text"].as_str().unwrap_or_default().to_string())
    }

    async fn transcribe_local(&self, wav_bytes: Vec<u8>) -> Result<String> {
        let _ = wav_bytes;
        Ok(String::new())
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum TtsBackend {
    System,
    OpenAI,
}

impl TtsBackend {
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "system" => Some(Self::System),
            "openai" => Some(Self::OpenAI),
            _ => None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct VoiceOutputConfig {
    pub enabled: bool,
    pub backend: TtsBackend,
    pub voice: String,
    pub speed: f32,
}

impl Default for VoiceOutputConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            backend: TtsBackend::System,
            voice: "alloy".to_string(),
            speed: 1.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VoiceCommand {
    On,
    Off,
    Status,
}

impl VoiceCommand {
    #[must_use]
    pub fn parse(input: &str) -> Option<Self> {
        let parts: Vec<&str> = input.trim().splitn(3, ' ').collect();
        if parts.first() != Some(&"/voice") {
            return None;
        }
        match parts.get(1).copied() {
            Some("on") => Some(Self::On),
            Some("off") => Some(Self::Off),
            Some("status") => Some(Self::Status),
            _ => None,
        }
    }
}

pub struct VoiceOutput {
    pub config: VoiceOutputConfig,
}

impl VoiceOutput {
    #[must_use]
    pub fn new(config: VoiceOutputConfig) -> Self {
        Self { config }
    }

    pub async fn speak(&self, text: &str) -> Result<()> {
        if !self.config.enabled {
            return Ok(());
        }
        match self.config.backend {
            TtsBackend::System => self.speak_system(text).await,
            TtsBackend::OpenAI => self.speak_openai(text).await,
        }
    }

    async fn speak_system(&self, text: &str) -> Result<()> {
        let cmd = if cfg!(target_os = "macos") { "say" } else { "espeak" };
        tokio::process::Command::new(cmd).arg(text).status().await?;
        Ok(())
    }

    async fn speak_openai(&self, text: &str) -> Result<()> {
        let api_key = std::env::var("OPENAI_API_KEY").map_err(|_| anyhow!("OPENAI_API_KEY not set"))?;
        let client = reqwest::Client::new();
        let body = serde_json::json!({
            "model": "tts-1",
            "input": text,
            "voice": self.config.voice,
            "speed": self.config.speed,
        });
        let audio_bytes = client
            .post("https://api.openai.com/v1/audio/speech")
            .bearer_auth(api_key)
            .json(&body)
            .send()
            .await?
            .bytes()
            .await?;
        let _ = audio_bytes;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn voice_input_config_defaults() {
        let cfg = VoiceInputConfig::default();
        assert_eq!(cfg.sample_rate, 16_000);
        assert_eq!(cfg.channels, 1);
        assert!(!cfg.vad_enabled || cfg.vad_silence_threshold_ms == 500);
    }

    #[test]
    fn whisper_backend_from_str() {
        assert_eq!(WhisperBackend::parse("openai"), Some(WhisperBackend::OpenAI));
        assert_eq!(WhisperBackend::parse("local"), Some(WhisperBackend::Local));
        assert_eq!(WhisperBackend::parse("unknown"), None);
    }

    #[test]
    fn wav_header_for_samples_has_correct_size() {
        let header = VoiceInput::encode_wav_header(16_000, 1, 1_000);
        assert_eq!(header.len(), 44);
        assert_eq!(&header[0..4], b"RIFF");
        assert_eq!(&header[8..12], b"WAVE");
    }

    #[test]
    fn voice_output_config_defaults() {
        let cfg = VoiceOutputConfig::default();
        assert!(!cfg.enabled);
        assert_eq!(cfg.backend, TtsBackend::System);
        assert_eq!(cfg.speed, 1.0);
    }

    #[test]
    fn tts_backend_from_str() {
        assert_eq!(TtsBackend::parse("openai"), Some(TtsBackend::OpenAI));
        assert_eq!(TtsBackend::parse("system"), Some(TtsBackend::System));
        assert_eq!(TtsBackend::parse("bad"), None);
    }

    #[test]
    fn voice_command_parsing() {
        assert_eq!(VoiceCommand::parse("/voice on"), Some(VoiceCommand::On));
        assert_eq!(VoiceCommand::parse("/voice off"), Some(VoiceCommand::Off));
        assert_eq!(VoiceCommand::parse("/voice status"), Some(VoiceCommand::Status));
        assert_eq!(VoiceCommand::parse("/voice"), None);
    }
}
