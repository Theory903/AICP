use anyhow::{bail, Result};

use crate::session::Session;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SessionCommand {
    New { name: String },
    List,
    Switch { name: String },
    Close { name: String },
}

impl SessionCommand {
    #[must_use]
    pub fn parse(input: &str) -> Option<Self> {
        let parts: Vec<&str> = input.trim().splitn(4, ' ').collect();
        if parts.first() != Some(&"/session") {
            return None;
        }
        match parts.get(1).copied() {
            Some("new") => Some(Self::New {
                name: parts.get(2).unwrap_or(&"session").to_string(),
            }),
            Some("list") => Some(Self::List),
            Some("switch") => Some(Self::Switch {
                name: parts.get(2)?.to_string(),
            }),
            Some("close") => Some(Self::Close {
                name: parts.get(2)?.to_string(),
            }),
            _ => None,
        }
    }
}

pub struct SessionMux {
    sessions: indexmap::IndexMap<String, Session>,
    active: String,
}

impl SessionMux {
    #[must_use]
    pub fn new() -> Self {
        let mut sessions = indexmap::IndexMap::new();
        let name = "session-1".to_string();
        sessions.insert(name.clone(), Session::new());
        Self {
            sessions,
            active: name,
        }
    }

    #[must_use]
    pub fn session_count(&self) -> usize {
        self.sessions.len()
    }

    #[must_use]
    pub fn active_session_name(&self) -> &str {
        &self.active
    }

    #[must_use]
    pub fn active_session(&self) -> &Session {
        self.sessions
            .get(&self.active)
            .expect("active session must exist")
    }

    pub fn active_session_mut(&mut self) -> &mut Session {
        self.sessions
            .get_mut(&self.active)
            .expect("active session must exist")
    }

    pub fn create(&mut self, name: &str) -> Result<()> {
        if name.is_empty() {
            bail!("session name cannot be empty");
        }
        if self.sessions.contains_key(name) {
            bail!("session '{name}' already exists");
        }
        self.sessions.insert(name.to_string(), Session::new());
        Ok(())
    }

    pub fn switch(&mut self, name: &str) -> Result<()> {
        if !self.sessions.contains_key(name) {
            bail!("session '{name}' not found");
        }
        self.active = name.to_string();
        Ok(())
    }

    pub fn close(&mut self, name: &str) -> Result<()> {
        if self.sessions.len() == 1 {
            bail!("cannot close the last session");
        }
        if !self.sessions.contains_key(name) {
            bail!("session '{name}' not found");
        }
        self.sessions.shift_remove(name);
        if self.active == name {
            self.active = self
                .sessions
                .keys()
                .next()
                .expect("at least one remains")
                .clone();
        }
        Ok(())
    }

    #[must_use]
    pub fn list(&self) -> Vec<String> {
        self.sessions.keys().cloned().collect()
    }
}

impl Default for SessionMux {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_session_mux_has_one_default_session() {
        let mux = SessionMux::new();
        assert_eq!(mux.session_count(), 1);
        assert!(mux.active_session_name().starts_with("session-"));
    }

    #[test]
    fn create_and_switch_named_session() {
        let mut mux = SessionMux::new();
        mux.create("work").expect("create work session");
        assert_eq!(mux.session_count(), 2);
        mux.switch("work").expect("switch to work");
        assert_eq!(mux.active_session_name(), "work");
    }

    #[test]
    fn close_session_removes_it() {
        let mut mux = SessionMux::new();
        mux.create("temp").expect("create temp");
        mux.switch("temp").expect("switch to temp");
        mux.close("temp").expect("close temp");
        assert_eq!(mux.session_count(), 1);
        assert_ne!(mux.active_session_name(), "temp");
    }

    #[test]
    fn list_returns_all_session_names() {
        let mut mux = SessionMux::new();
        mux.create("alpha").expect("alpha");
        mux.create("beta").expect("beta");
        let names = mux.list();
        assert!(names.contains(&"alpha".to_string()));
        assert!(names.contains(&"beta".to_string()));
        assert_eq!(names.len(), 3);
    }

    #[test]
    fn parse_session_command() {
        assert_eq!(
            SessionCommand::parse("/session new work"),
            Some(SessionCommand::New {
                name: "work".to_string()
            })
        );
        assert_eq!(
            SessionCommand::parse("/session list"),
            Some(SessionCommand::List)
        );
        assert_eq!(
            SessionCommand::parse("/session switch alpha"),
            Some(SessionCommand::Switch {
                name: "alpha".to_string()
            })
        );
        assert_eq!(
            SessionCommand::parse("/session close beta"),
            Some(SessionCommand::Close {
                name: "beta".to_string()
            })
        );
        assert_eq!(SessionCommand::parse("/ask something"), None);
    }
}
