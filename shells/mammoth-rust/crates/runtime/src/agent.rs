use std::sync::mpsc::{sync_channel, Receiver, SyncSender, TryRecvError};
use std::sync::Mutex;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AgentKind {
    Orchestrator,
    Specialist,
    Worker,
    Supervisor,
}

#[derive(Debug, Clone)]
pub struct AgentConfig {
    pub name: String,
    pub kind: AgentKind,
    pub model: Option<String>,
    pub system_prompt: Option<String>,
    pub skills: Vec<String>,
    pub max_turns: u32,
    pub temperature: Option<f32>,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            name: "default".to_string(),
            kind: AgentKind::Worker,
            model: None,
            system_prompt: None,
            skills: vec![],
            max_turns: 20,
            temperature: None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct TeamPreset {
    pub name: String,
    pub agents: Vec<AgentConfig>,
    pub coordinator: String,
}

pub struct AgentChannel {
    sender: SyncSender<AgentMessage>,
    receiver: Mutex<Receiver<AgentMessage>>,
}

#[derive(Debug, Clone)]
pub struct AgentMessage {
    pub from: String,
    pub to: String,
    pub content: String,
    pub message_type: AgentMessageType,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AgentMessageType {
    Task,
    Result,
    Error,
    Broadcast,
}

impl AgentChannel {
    #[must_use]
    pub fn new(capacity: usize) -> Self {
        let (sender, receiver) = sync_channel(capacity.max(1));
        Self {
            sender,
            receiver: Mutex::new(receiver),
        }
    }

    pub fn send(&self, msg: AgentMessage) -> Result<(), String> {
        self.sender.send(msg).map_err(|error| error.to_string())
    }

    #[must_use]
    pub fn try_recv(&self) -> Option<AgentMessage> {
        self.receiver
            .lock()
            .ok()
            .and_then(|receiver| match receiver.try_recv() {
                Ok(message) => Some(message),
                Err(TryRecvError::Empty | TryRecvError::Disconnected) => None,
            })
    }
}

pub struct CoordinatorLoop {
    config: AgentConfig,
    team: Vec<AgentConfig>,
    channel: AgentChannel,
}

impl CoordinatorLoop {
    #[must_use]
    pub fn new(coordinator: AgentConfig, team: Vec<AgentConfig>) -> Self {
        Self {
            config: coordinator,
            team,
            channel: AgentChannel::new(32),
        }
    }

    pub fn dispatch(&self, task: &str, target: &str) -> Result<(), String> {
        if !self.team.iter().any(|agent| agent.name == target) {
            return Err(format!("unknown agent target: {target}"));
        }
        self.channel.send(AgentMessage {
            from: self.config.name.clone(),
            to: target.to_string(),
            content: task.to_string(),
            message_type: AgentMessageType::Task,
        })
    }

    #[must_use]
    pub fn collect_results(&self, timeout_ms: u64) -> Vec<AgentMessage> {
        let deadline = Instant::now() + Duration::from_millis(timeout_ms);
        let mut messages = Vec::new();
        while Instant::now() < deadline {
            if let Some(message) = self.channel.try_recv() {
                messages.push(message);
                continue;
            }
            std::thread::sleep(Duration::from_millis(5));
        }
        messages
    }
}

#[cfg(test)]
mod tests {
    use super::{AgentConfig, AgentKind, AgentMessage, AgentMessageType, CoordinatorLoop};

    #[test]
    fn dispatches_messages_to_known_agents() {
        let coordinator = AgentConfig {
            name: "coord".to_string(),
            kind: AgentKind::Orchestrator,
            ..AgentConfig::default()
        };
        let loop_state = CoordinatorLoop::new(
            coordinator,
            vec![AgentConfig {
                name: "worker-a".to_string(),
                ..AgentConfig::default()
            }],
        );

        loop_state
            .dispatch("run task", "worker-a")
            .expect("dispatch should work");
        let messages = loop_state.collect_results(20);
        assert_eq!(messages.len(), 1);
        assert_eq!(messages[0].message_type, AgentMessageType::Task);
        assert_eq!(messages[0].to, "worker-a");
    }

    #[test]
    fn rejects_unknown_dispatch_target() {
        let loop_state = CoordinatorLoop::new(AgentConfig::default(), vec![]);
        let error = loop_state
            .dispatch("run task", "missing")
            .expect_err("unknown target should fail");
        assert!(error.contains("unknown agent target"));
    }

    #[test]
    fn channel_try_recv_returns_none_when_empty() {
        let loop_state = CoordinatorLoop::new(AgentConfig::default(), vec![]);
        let messages = loop_state.collect_results(1);
        assert!(messages.is_empty());
        let _ = AgentMessage {
            from: String::new(),
            to: String::new(),
            content: String::new(),
            message_type: AgentMessageType::Broadcast,
        };
    }
}
