use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::time::Instant;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpanRecord {
    pub name: String,
    pub start_ms: u64,
    pub duration_ms: u64,
    pub parent: Option<String>,
}

struct SpanState {
    records: Vec<SpanRecord>,
}

pub struct PerformanceTracer {
    state: Arc<Mutex<SpanState>>,
    epoch: Instant,
}

impl PerformanceTracer {
    #[must_use]
    pub fn new() -> Self {
        Self {
            state: Arc::new(Mutex::new(SpanState {
                records: Vec::new(),
            })),
            epoch: Instant::now(),
        }
    }

    #[must_use]
    pub fn start_span(&self, name: &str) -> SpanHandle {
        SpanHandle {
            name: name.to_string(),
            started: Instant::now(),
            start_ms: u64::try_from(self.epoch.elapsed().as_millis()).unwrap_or(0),
            state: Arc::clone(&self.state),
            parent: None,
            finished: false,
        }
    }

    #[must_use]
    pub fn report(&self) -> Vec<SpanRecord> {
        let state = self.state.lock().expect("tracer lock");
        let mut records = state.records.clone();
        records.sort_by_key(|r| r.start_ms);
        records
    }
}

impl Default for PerformanceTracer {
    fn default() -> Self {
        Self::new()
    }
}

pub struct SpanHandle {
    name: String,
    started: Instant,
    start_ms: u64,
    state: Arc<Mutex<SpanState>>,
    parent: Option<String>,
    finished: bool,
}

impl SpanHandle {
    pub fn finish(mut self) {
        self.record();
        self.finished = true;
    }

    #[must_use]
    pub fn child(&self, name: &str) -> SpanHandle {
        SpanHandle {
            name: name.to_string(),
            started: Instant::now(),
            start_ms: self.start_ms
                + u64::try_from(self.started.elapsed().as_millis()).unwrap_or(0),
            state: Arc::clone(&self.state),
            parent: Some(self.name.clone()),
            finished: false,
        }
    }

    fn record(&self) {
        let duration_ms = u64::try_from(self.started.elapsed().as_millis()).unwrap_or(0);
        let record = SpanRecord {
            name: self.name.clone(),
            start_ms: self.start_ms,
            duration_ms,
            parent: self.parent.clone(),
        };
        if let Ok(mut state) = self.state.lock() {
            state.records.push(record);
        }
    }
}

impl Drop for SpanHandle {
    fn drop(&mut self) {
        if !self.finished {
            self.record();
        }
    }
}
