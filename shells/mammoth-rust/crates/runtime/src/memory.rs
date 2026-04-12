use std::collections::{HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EpisodicEntry {
    pub id: String,
    pub timestamp: u64,
    pub content: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkingMemoryItem {
    pub key: String,
    pub value: String,
    pub ttl_seconds: Option<u64>,
    pub created_at: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EntityRecord {
    pub entity_id: String,
    pub entity_type: String,
    pub attributes: HashMap<String, String>,
    pub last_seen: u64,
}

pub struct MemoryStore {
    episodic: VecDeque<EpisodicEntry>,
    working: HashMap<String, WorkingMemoryItem>,
    entities: HashMap<String, EntityRecord>,
    max_episodic: usize,
}

impl MemoryStore {
    #[must_use]
    pub fn new(max_episodic: usize) -> Self {
        Self {
            episodic: VecDeque::new(),
            working: HashMap::new(),
            entities: HashMap::new(),
            max_episodic: max_episodic.max(1),
        }
    }

    pub fn push_episode(&mut self, content: &str, tags: Vec<String>) -> String {
        let timestamp = now_unix_seconds();
        let id = format!("episode-{timestamp}-{}", self.episodic.len() + 1);
        self.episodic.push_back(EpisodicEntry {
            id: id.clone(),
            timestamp,
            content: content.to_string(),
            tags,
        });
        while self.episodic.len() > self.max_episodic {
            let _ = self.episodic.pop_front();
        }
        id
    }

    #[must_use]
    pub fn recent_episodes(&self, n: usize) -> Vec<&EpisodicEntry> {
        self.episodic.iter().rev().take(n).collect()
    }

    pub fn set_working(&mut self, key: &str, value: &str, ttl_seconds: Option<u64>) {
        self.working.insert(
            key.to_string(),
            WorkingMemoryItem {
                key: key.to_string(),
                value: value.to_string(),
                ttl_seconds,
                created_at: now_unix_seconds(),
            },
        );
    }

    #[must_use]
    pub fn get_working(&self, key: &str) -> Option<&str> {
        let item = self.working.get(key)?;
        if item
            .ttl_seconds
            .is_some_and(|ttl| now_unix_seconds().saturating_sub(item.created_at) > ttl)
        {
            return None;
        }
        Some(item.value.as_str())
    }

    pub fn evict_expired_working(&mut self) {
        let now = now_unix_seconds();
        self.working.retain(|_, item| {
            item.ttl_seconds
                .is_none_or(|ttl| now.saturating_sub(item.created_at) <= ttl)
        });
    }

    pub fn upsert_entity(&mut self, id: &str, entity_type: &str, attrs: HashMap<String, String>) {
        self.entities.insert(
            id.to_string(),
            EntityRecord {
                entity_id: id.to_string(),
                entity_type: entity_type.to_string(),
                attributes: attrs,
                last_seen: now_unix_seconds(),
            },
        );
    }

    #[must_use]
    pub fn get_entity(&self, id: &str) -> Option<&EntityRecord> {
        self.entities.get(id)
    }

    #[must_use]
    pub fn working_snapshot(&self) -> HashMap<String, String> {
        self.working
            .iter()
            .filter_map(|(key, _)| {
                self.get_working(key)
                    .map(|value| (key.clone(), value.to_string()))
            })
            .collect()
    }

    #[must_use]
    pub fn summarize_for_prompt(&self, max_episodes: usize) -> String {
        let mut lines = vec!["# Memory context".to_string()];
        let working = self.working_snapshot();
        if !working.is_empty() {
            lines.push("Working memory:".to_string());
            for (key, value) in working {
                lines.push(format!(" - {key}: {value}"));
            }
        }
        let episodes = self.recent_episodes(max_episodes);
        if !episodes.is_empty() {
            lines.push("Recent episodic memory:".to_string());
            for episode in episodes {
                let tags = if episode.tags.is_empty() {
                    String::new()
                } else {
                    format!(" [{}]", episode.tags.join(", "))
                };
                lines.push(format!(" - {}{}", episode.content, tags));
            }
        }
        if self.entities.is_empty() {
            lines.push("Entities: none tracked".to_string());
        } else {
            lines.push(format!("Entities tracked: {}", self.entities.len()));
        }
        lines.join("\n")
    }
}

fn now_unix_seconds() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_secs())
}

#[cfg(test)]
mod tests {
    use super::MemoryStore;
    use std::collections::HashMap;

    #[test]
    fn stores_recent_episodes_and_working_memory() {
        let mut store = MemoryStore::new(2);
        store.push_episode("first", vec!["a".to_string()]);
        store.push_episode("second", vec!["b".to_string()]);
        store.push_episode("third", vec!["c".to_string()]);
        store.set_working("focus", "runtime", None);

        assert_eq!(store.recent_episodes(5).len(), 2);
        assert_eq!(store.get_working("focus"), Some("runtime"));
    }

    #[test]
    fn stores_entities() {
        let mut store = MemoryStore::new(4);
        let mut attrs = HashMap::new();
        attrs.insert("role".to_string(), "worker".to_string());
        store.upsert_entity("agent-1", "agent", attrs);

        let entity = store.get_entity("agent-1").expect("entity should exist");
        assert_eq!(entity.entity_type, "agent");
        assert_eq!(
            entity.attributes.get("role").map(String::as_str),
            Some("worker")
        );
    }
}
