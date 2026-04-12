use mammoth_runtime::{
    adapter::{AdapterConfig, NormalizedMessage},
    adapter_registry::{ChannelAdapterRegistry, ChannelsConfig},
    session_export::{ExportFormat, SessionExporter},
    session_mux::{SessionCommand, SessionMux},
    ssh::SshSessionConfig,
    voice::{TtsBackend, VoiceCommand, VoiceOutputConfig, WhisperBackend},
};

#[test]
fn channels_config_round_trips_through_toml() {
    let registry = ChannelAdapterRegistry::default();
    assert!(registry.platform_names().is_empty());

    let original = ChannelsConfig {
        channels: vec![
            AdapterConfig::Telegram {
                bot_token: "tg_tok".to_string(),
            },
            AdapterConfig::Discord {
                bot_token: "dc_tok".to_string(),
                application_id: 99_999,
            },
            AdapterConfig::Slack {
                bot_token: "xoxb-slack".to_string(),
                signing_secret: "sl_secret".to_string(),
                app_token: None,
            },
        ],
    };
    let toml_str = toml::to_string(&original).expect("serialize");
    let parsed: ChannelsConfig = toml::from_str(&toml_str).expect("deserialize");
    assert_eq!(parsed.channels.len(), 3);
}

#[test]
fn session_mux_full_lifecycle() {
    let mut mux = SessionMux::new();
    mux.create("alpha").expect("alpha");
    mux.create("beta").expect("beta");
    assert_eq!(mux.session_count(), 3);
    mux.switch("alpha").expect("switch");
    assert_eq!(mux.active_session_name(), "alpha");
    mux.close("beta").expect("close beta");
    let names = mux.list();
    assert!(!names.contains(&"beta".to_string()));
    assert_eq!(mux.session_count(), 2);
    mux.switch("alpha").expect("re-switch");
    mux.close("alpha").expect("close active");
    assert_ne!(mux.active_session_name(), "alpha");
}

#[test]
fn session_command_full_parse_suite() {
    let cases = vec![
        (
            "/session new mywork",
            SessionCommand::New {
                name: "mywork".to_string(),
            },
        ),
        ("/session list", SessionCommand::List),
        (
            "/session switch mywork",
            SessionCommand::Switch {
                name: "mywork".to_string(),
            },
        ),
        (
            "/session close mywork",
            SessionCommand::Close {
                name: "mywork".to_string(),
            },
        ),
    ];
    for (input, expected) in cases {
        assert_eq!(
            SessionCommand::parse(input),
            Some(expected),
            "failed on: {input}"
        );
    }
}

#[test]
fn session_exporter_both_formats_non_empty() {
    use mammoth_runtime::session::Session;

    let mut session = Session::new();
    session
        .messages
        .push(mammoth_runtime::session::ConversationMessage::user_text(
            "Summarise the logs",
        ));
    session.messages.push(
        mammoth_runtime::session::ConversationMessage::assistant_text("The logs show 3 errors."),
    );

    let exporter = SessionExporter::new(&session);
    let json = exporter.export(ExportFormat::Json).expect("json export");
    let md = exporter
        .export(ExportFormat::Markdown)
        .expect("markdown export");

    assert!(json.len() > 10);
    assert!(md.contains("## User"));
    assert!(md.contains("Summarise the logs"));
    assert!(md.contains("3 errors"));
}

#[test]
fn ssh_config_full_url_round_trip() {
    let url = "ssh://deploy@build.internal:2222";
    let cfg = SshSessionConfig::from_url(url).expect("parse");
    assert_eq!(cfg.host, "build.internal");
    assert_eq!(cfg.port, 2222);
    assert_eq!(cfg.user, "deploy");
    assert!(cfg.host_key_verification);
}

#[test]
fn webhook_signature_integration() {
    use mammoth_server::webhook::WebhookTrigger;

    let secret = "integration_secret";
    let payload = b"{'session_id':'session-1','message':'run tests'}";
    let sig = WebhookTrigger::compute_signature(secret, payload);
    assert!(sig.starts_with("v0="));
    assert!(WebhookTrigger::verify_signature(secret, &sig, payload));
    assert!(!WebhookTrigger::verify_signature("wrong", &sig, payload));
    assert!(!WebhookTrigger::verify_signature(secret, &sig, b"tampered"));
}

#[test]
fn voice_config_integration() {
    let input_cfg = mammoth_runtime::voice::VoiceInputConfig {
        backend: WhisperBackend::Local,
        vad_enabled: false,
        ..Default::default()
    };
    assert_eq!(input_cfg.backend, WhisperBackend::Local);
    assert!(!input_cfg.vad_enabled);

    let output_cfg = VoiceOutputConfig {
        enabled: true,
        backend: TtsBackend::OpenAI,
        voice: "nova".to_string(),
        speed: 1.25,
    };
    assert!(output_cfg.enabled);
    assert_eq!(output_cfg.voice, "nova");
    assert_eq!(VoiceCommand::parse("/voice on"), Some(VoiceCommand::On));
    assert_eq!(VoiceCommand::parse("/voice off"), Some(VoiceCommand::Off));
}

#[test]
fn normalized_message_metadata_roundtrip() {
    use std::collections::HashMap;

    let mut meta = HashMap::new();
    meta.insert("guild_id".to_string(), "123456".to_string());
    meta.insert("thread_id".to_string(), "987654".to_string());

    let msg = NormalizedMessage {
        platform: "discord".to_string(),
        channel_id: "general".to_string(),
        sender_id: "user_abc".to_string(),
        text: "Please deploy to staging".to_string(),
        metadata: meta.clone(),
    };
    let json = serde_json::to_string(&msg).expect("serialize");
    let back: NormalizedMessage = serde_json::from_str(&json).expect("deserialize");
    assert_eq!(back.metadata, meta);
    assert_eq!(back.platform, "discord");
}
