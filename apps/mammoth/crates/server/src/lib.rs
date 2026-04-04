use std::collections::HashMap;
use std::convert::Infallible;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use async_stream::stream;
use axum::extract::{Path, State};
use axum::http::{HeaderValue, StatusCode};
use axum::response::sse::{Event, KeepAlive, Sse};
use axum::response::{Html, IntoResponse};
use axum::routing::{get, post};
use axum::{Json, Router};
use runtime::{ConversationMessage, Session as RuntimeSession};
use serde::{Deserialize, Serialize};
use tokio::sync::{broadcast, RwLock};

// ---------------------------------------------------------------------------
// TurnRunner — injected AI inference backend
// ---------------------------------------------------------------------------

/// Executes one conversation turn given the current history and a new user
/// message. Returns the new assistant messages produced during the turn.
///
/// The trait is object-safe and `Send + Sync` so it can live in `AppState`.
/// Implementations run synchronously (the `server` crate's tokio runtime calls
/// `spawn_blocking` around the invocation so the async event loop is never
/// blocked).
pub trait TurnRunner: Send + Sync {
    fn run_turn(
        &self,
        history: Vec<ConversationMessage>,
        user_message: String,
    ) -> Result<Vec<ConversationMessage>, String>;
}

pub type SessionId = String;
pub type SessionStore = Arc<RwLock<HashMap<SessionId, Session>>>;

/// Shared state for the extension bridge SSE channel.
/// One broadcast channel for all connected extension clients.
pub type ExtBroadcast = broadcast::Sender<ExtEvent>;

const BROADCAST_CAPACITY: usize = 64;

#[derive(Clone)]
pub struct AppState {
    sessions: SessionStore,
    next_session_id: Arc<AtomicU64>,
    /// Broadcast channel for the Chrome extension bridge.
    ext_events: ExtBroadcast,
    /// Optional AI inference backend. When present, each user message triggers
    /// a conversation turn and the assistant response is streamed back over SSE.
    runner: Option<Arc<dyn TurnRunner>>,
}

impl AppState {
    #[must_use]
    pub fn new() -> Self {
        let (ext_events, _) = broadcast::channel(BROADCAST_CAPACITY);
        Self {
            sessions: Arc::new(RwLock::new(HashMap::new())),
            next_session_id: Arc::new(AtomicU64::new(1)),
            ext_events,
            runner: None,
        }
    }

    /// Attach an AI inference backend so the web channel can respond to messages.
    #[must_use]
    pub fn with_runner(mut self, runner: Arc<dyn TurnRunner>) -> Self {
        self.runner = Some(runner);
        self
    }

    fn allocate_session_id(&self) -> SessionId {
        let id = self.next_session_id.fetch_add(1, Ordering::Relaxed);
        format!("session-{id}")
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Clone)]
pub struct Session {
    pub id: SessionId,
    pub created_at: u64,
    pub conversation: RuntimeSession,
    events: broadcast::Sender<SessionEvent>,
}

impl Session {
    fn new(id: SessionId) -> Self {
        let (events, _) = broadcast::channel(BROADCAST_CAPACITY);
        Self {
            id,
            created_at: unix_timestamp_millis(),
            conversation: RuntimeSession::new(),
            events,
        }
    }

    fn subscribe(&self) -> broadcast::Receiver<SessionEvent> {
        self.events.subscribe()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "type", rename_all = "snake_case")]
enum SessionEvent {
    Snapshot {
        session_id: SessionId,
        session: RuntimeSession,
    },
    Message {
        session_id: SessionId,
        message: ConversationMessage,
    },
}

impl SessionEvent {
    fn event_name(&self) -> &'static str {
        match self {
            Self::Snapshot { .. } => "snapshot",
            Self::Message { .. } => "message",
        }
    }

    fn to_sse_event(&self) -> Result<Event, serde_json::Error> {
        Ok(Event::default()
            .event(self.event_name())
            .data(serde_json::to_string(self)?))
    }
}

/// Events forwarded to the Chrome extension bridge SSE stream.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ExtEvent {
    /// A new message to display in the extension popup.
    Message { content: String },
    /// An approval request that the extension must surface to the user.
    ApprovalRequest {
        approval_id: String,
        capability_name: String,
        description: String,
    },
}

impl ExtEvent {
    fn event_name(&self) -> &'static str {
        match self {
            Self::Message { .. } => "message",
            Self::ApprovalRequest { .. } => "approval_request",
        }
    }

    fn to_sse_event(&self) -> Result<Event, serde_json::Error> {
        Ok(Event::default()
            .event(self.event_name())
            .data(serde_json::to_string(self)?))
    }
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

type ApiError = (StatusCode, Json<ErrorResponse>);
type ApiResult<T> = Result<T, ApiError>;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CreateSessionResponse {
    pub session_id: SessionId,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SessionSummary {
    pub id: SessionId,
    pub created_at: u64,
    pub message_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ListSessionsResponse {
    pub sessions: Vec<SessionSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SessionDetailsResponse {
    pub id: SessionId,
    pub created_at: u64,
    pub session: RuntimeSession,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SendMessageRequest {
    pub message: String,
}

pub fn app(state: AppState) -> Router {
    Router::new()
        // Health check
        .route("/health", get(health_check))
        // Studio web UI (Mammoth Web channel)
        .route("/", get(studio_index))
        // Session API (Mammoth Web channel sessions)
        .route("/sessions", post(create_session).get(list_sessions))
        .route("/sessions/{id}", get(get_session))
        .route("/sessions/{id}/events", get(stream_session_events))
        .route("/sessions/{id}/message", post(send_message))
        // Chrome extension bridge (Mammoth Extension channel)
        .route("/ext/events", get(ext_stream_events))
        .route("/ext/message", post(ext_send_message))
        .with_state(state)
}

async fn create_session(
    State(state): State<AppState>,
) -> (StatusCode, Json<CreateSessionResponse>) {
    let session_id = state.allocate_session_id();
    let session = Session::new(session_id.clone());

    state
        .sessions
        .write()
        .await
        .insert(session_id.clone(), session);

    (
        StatusCode::CREATED,
        Json(CreateSessionResponse { session_id }),
    )
}

async fn list_sessions(State(state): State<AppState>) -> Json<ListSessionsResponse> {
    let sessions = state.sessions.read().await;
    let mut summaries = sessions
        .values()
        .map(|session| SessionSummary {
            id: session.id.clone(),
            created_at: session.created_at,
            message_count: session.conversation.messages.len(),
        })
        .collect::<Vec<_>>();
    summaries.sort_by(|left, right| left.id.cmp(&right.id));

    Json(ListSessionsResponse {
        sessions: summaries,
    })
}

async fn get_session(
    State(state): State<AppState>,
    Path(id): Path<SessionId>,
) -> ApiResult<Json<SessionDetailsResponse>> {
    let sessions = state.sessions.read().await;
    let session = sessions
        .get(&id)
        .ok_or_else(|| not_found(format!("session `{id}` not found")))?;

    Ok(Json(SessionDetailsResponse {
        id: session.id.clone(),
        created_at: session.created_at,
        session: session.conversation.clone(),
    }))
}

async fn send_message(
    State(state): State<AppState>,
    Path(id): Path<SessionId>,
    Json(payload): Json<SendMessageRequest>,
) -> ApiResult<StatusCode> {
    let user_message = ConversationMessage::user_text(payload.message.clone());

    // Store user message and capture broadcaster + runner + history snapshot.
    let (broadcaster, runner, history) = {
        let mut sessions = state.sessions.write().await;
        let session = sessions
            .get_mut(&id)
            .ok_or_else(|| not_found(format!("session `{id}` not found")))?;
        session.conversation.messages.push(user_message.clone());
        let history = session.conversation.messages.clone();
        (session.events.clone(), state.runner.clone(), history)
    };

    // Broadcast the user message immediately so SSE clients see it.
    let _ = broadcaster.send(SessionEvent::Message {
        session_id: id.clone(),
        message: user_message,
    });

    // If a runner is configured, spawn a blocking task to run inference and
    // stream the assistant reply back over SSE.
    if let Some(runner) = runner {
        let sessions = state.sessions.clone();
        let session_id = id.clone();
        let user_text = payload.message.clone();

        // history already includes the user message we just pushed
        tokio::task::spawn_blocking(move || {
            match runner.run_turn(history, user_text) {
                Ok(new_messages) => {
                    // Persist assistant messages and broadcast each one.
                    let rt = tokio::runtime::Handle::try_current();
                    let update_and_broadcast = async {
                        let mut store = sessions.write().await;
                        if let Some(session) = store.get_mut(&session_id) {
                            for msg in &new_messages {
                                session.conversation.messages.push(msg.clone());
                                let _ = broadcaster.send(SessionEvent::Message {
                                    session_id: session_id.clone(),
                                    message: msg.clone(),
                                });
                            }
                        }
                    };
                    if let Ok(handle) = rt {
                        handle.block_on(update_and_broadcast);
                    }
                }
                Err(error) => {
                    // Broadcast a synthetic error message so the UI sees it.
                    let err_msg = ConversationMessage::user_text(format!("[error] {error}"));
                    let _ = broadcaster.send(SessionEvent::Message {
                        session_id: session_id.clone(),
                        message: err_msg,
                    });
                }
            }
        });
    }

    Ok(StatusCode::NO_CONTENT)
}

async fn stream_session_events(
    State(state): State<AppState>,
    Path(id): Path<SessionId>,
) -> ApiResult<impl IntoResponse> {
    let (snapshot, mut receiver) = {
        let sessions = state.sessions.read().await;
        let session = sessions
            .get(&id)
            .ok_or_else(|| not_found(format!("session `{id}` not found")))?;
        (
            SessionEvent::Snapshot {
                session_id: session.id.clone(),
                session: session.conversation.clone(),
            },
            session.subscribe(),
        )
    };

    let stream = stream! {
        if let Ok(event) = snapshot.to_sse_event() {
            yield Ok::<Event, Infallible>(event);
        }

        loop {
            match receiver.recv().await {
                Ok(event) => {
                    if let Ok(sse_event) = event.to_sse_event() {
                        yield Ok::<Event, Infallible>(sse_event);
                    }
                }
                Err(broadcast::error::RecvError::Lagged(_)) => {}
                Err(broadcast::error::RecvError::Closed) => break,
            }
        }
    };

    Ok(Sse::new(stream).keep_alive(KeepAlive::new().interval(Duration::from_secs(15))))
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

async fn health_check() -> impl IntoResponse {
    (
        StatusCode::OK,
        [(axum::http::header::CONTENT_TYPE, HeaderValue::from_static("application/json"))],
        r#"{"status":"ok","service":"mammoth-web"}"#,
    )
}

// ---------------------------------------------------------------------------
// Studio web UI (Mammoth Web channel)
// ---------------------------------------------------------------------------

/// Minimal Studio HTML stub — the Mammoth Web channel's supervision console.
///
/// This will be replaced by a full SPA build served from a static directory.
/// Until then it provides a functional skeleton for integration tests.
async fn studio_index() -> Html<&'static str> {
    Html(include_str!("studio.html"))
}

// ---------------------------------------------------------------------------
// Chrome extension bridge (Mammoth Extension channel)
// ---------------------------------------------------------------------------

/// SSE stream consumed by the Chrome extension background service worker.
///
/// The extension connects here once and receives `ExtEvent`s pushed by the server
/// (assistant messages, approval requests, etc.).
async fn ext_stream_events(
    State(state): State<AppState>,
) -> impl IntoResponse {
    let mut receiver = state.ext_events.subscribe();

    let stream = stream! {
        loop {
            match receiver.recv().await {
                Ok(event) => {
                    if let Ok(sse_event) = event.to_sse_event() {
                        yield Ok::<Event, Infallible>(sse_event);
                    }
                }
                Err(broadcast::error::RecvError::Lagged(_)) => {}
                Err(broadcast::error::RecvError::Closed) => break,
            }
        }
    };

    Sse::new(stream).keep_alive(KeepAlive::new().interval(Duration::from_secs(15)))
}

/// Receive a message from the Chrome extension and broadcast it as an `ExtEvent`.
///
/// Used by the extension popup to send user messages into the Mammoth session.
async fn ext_send_message(
    State(state): State<AppState>,
    Json(payload): Json<SendMessageRequest>,
) -> StatusCode {
    let event = ExtEvent::Message { content: payload.message };
    let _ = state.ext_events.send(event);
    StatusCode::NO_CONTENT
}

fn unix_timestamp_millis() -> u64 {
    u64::try_from(
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time should be after epoch")
            .as_millis(),
    )
    .expect("timestamp fits in u64 until year 584556019")
}

fn not_found(message: String) -> ApiError {
    (
        StatusCode::NOT_FOUND,
        Json(ErrorResponse { error: message }),
    )
}

/// Convenience wrapper: bind and serve the Mammoth Web channel on an already-
/// bound `TcpListener`. Used by `mammoth-cli`'s `run_serve()` to avoid a
/// direct `axum` dependency in the CLI crate.
pub async fn serve(
    listener: tokio::net::TcpListener,
    state: AppState,
) -> Result<(), std::io::Error> {
    axum::serve(listener, app(state)).await
}

#[cfg(test)]
mod tests {
    use super::{
        app, AppState, CreateSessionResponse, ListSessionsResponse, SessionDetailsResponse,
    };
    use reqwest::Client;
    use std::net::SocketAddr;
    use std::time::Duration;
    use tokio::net::TcpListener;
    use tokio::task::JoinHandle;
    use tokio::time::timeout;

    struct TestServer {
        address: SocketAddr,
        handle: JoinHandle<()>,
    }

    impl TestServer {
        async fn spawn() -> Self {
            let listener = TcpListener::bind("127.0.0.1:0")
                .await
                .expect("test listener should bind");
            let address = listener
                .local_addr()
                .expect("listener should report local address");
            let handle = tokio::spawn(async move {
                axum::serve(listener, app(AppState::default()))
                    .await
                    .expect("server should run");
            });

            Self { address, handle }
        }

        fn url(&self, path: &str) -> String {
            format!("http://{}{}", self.address, path)
        }
    }

    impl Drop for TestServer {
        fn drop(&mut self) {
            self.handle.abort();
        }
    }

    async fn create_session(client: &Client, server: &TestServer) -> CreateSessionResponse {
        client
            .post(server.url("/sessions"))
            .send()
            .await
            .expect("create request should succeed")
            .error_for_status()
            .expect("create request should return success")
            .json::<CreateSessionResponse>()
            .await
            .expect("create response should parse")
    }

    async fn next_sse_frame(response: &mut reqwest::Response, buffer: &mut String) -> String {
        loop {
            if let Some(index) = buffer.find("\n\n") {
                let frame = buffer[..index].to_string();
                let remainder = buffer[index + 2..].to_string();
                *buffer = remainder;
                return frame;
            }

            let next_chunk = timeout(Duration::from_secs(5), response.chunk())
                .await
                .expect("SSE stream should yield within timeout")
                .expect("SSE stream should remain readable")
                .expect("SSE stream should stay open");
            buffer.push_str(&String::from_utf8_lossy(&next_chunk));
        }
    }

    #[tokio::test]
    async fn creates_and_lists_sessions() {
        let server = TestServer::spawn().await;
        let client = Client::new();

        // given
        let created = create_session(&client, &server).await;

        // when
        let sessions = client
            .get(server.url("/sessions"))
            .send()
            .await
            .expect("list request should succeed")
            .error_for_status()
            .expect("list request should return success")
            .json::<ListSessionsResponse>()
            .await
            .expect("list response should parse");
        let details = client
            .get(server.url(&format!("/sessions/{}", created.session_id)))
            .send()
            .await
            .expect("details request should succeed")
            .error_for_status()
            .expect("details request should return success")
            .json::<SessionDetailsResponse>()
            .await
            .expect("details response should parse");

        // then
        assert_eq!(created.session_id, "session-1");
        assert_eq!(sessions.sessions.len(), 1);
        assert_eq!(sessions.sessions[0].id, created.session_id);
        assert_eq!(sessions.sessions[0].message_count, 0);
        assert_eq!(details.id, "session-1");
        assert!(details.session.messages.is_empty());
    }

    #[tokio::test]
    async fn streams_message_events_and_persists_message_flow() {
        let server = TestServer::spawn().await;
        let client = Client::new();

        // given
        let created = create_session(&client, &server).await;
        let mut response = client
            .get(server.url(&format!("/sessions/{}/events", created.session_id)))
            .send()
            .await
            .expect("events request should succeed")
            .error_for_status()
            .expect("events request should return success");
        let mut buffer = String::new();
        let snapshot_frame = next_sse_frame(&mut response, &mut buffer).await;

        // when
        let send_status = client
            .post(server.url(&format!("/sessions/{}/message", created.session_id)))
            .json(&super::SendMessageRequest {
                message: "hello from test".to_string(),
            })
            .send()
            .await
            .expect("message request should succeed")
            .status();
        let message_frame = next_sse_frame(&mut response, &mut buffer).await;
        let details = client
            .get(server.url(&format!("/sessions/{}", created.session_id)))
            .send()
            .await
            .expect("details request should succeed")
            .error_for_status()
            .expect("details request should return success")
            .json::<SessionDetailsResponse>()
            .await
            .expect("details response should parse");

        // then
        assert_eq!(send_status, reqwest::StatusCode::NO_CONTENT);
        assert!(snapshot_frame.contains("event: snapshot"));
        assert!(snapshot_frame.contains("\"session_id\":\"session-1\""));
        assert!(message_frame.contains("event: message"));
        assert!(message_frame.contains("hello from test"));
        assert_eq!(details.session.messages.len(), 1);
        assert_eq!(
            details.session.messages[0],
            runtime::ConversationMessage::user_text("hello from test")
        );
    }
}
