// Human Cognitive Protocols - Supervision Dashboard Components
// Module 7 - 5-view dashboard: Live feed, approval queue, replay, risk, policy

use ratatui::prelude::*;
use std::collections::VecDeque;

/// Live Execution Feed View
pub struct LiveFeedView {
    max_items: usize,
    items: VecDeque<LiveFeedItem>,
}

#[derive(Debug, Clone)]
pub struct LiveFeedItem {
    pub execution_id: String,
    pub capability_name: String,
    pub status: ExecutionStatus,
    pub timestamp: String,
    pub actor: String,
    pub risk_score: Option<f32>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ExecutionStatus {
    Pending,
    Running,
    Success,
    Failed,
    Blocked,
}

impl LiveFeedView {
    pub fn new(max_items: usize) -> Self {
        Self {
            max_items,
            items: VecDeque::new(),
        }
    }

    pub fn add_item(&mut self, item: LiveFeedItem) {
        if self.items.len() >= self.max_items {
            self.items.pop_back();
        }
        self.items.push_front(item);
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        // Header
        let title = " Live Execution Feed ";
        buf.set_string(area.x, area.y, title, Style::default().bold());

        if self.items.is_empty() {
            buf.set_string(
                area.x + 2,
                area.y + 2,
                "No active executions",
                Style::default().dim(),
            );
            return;
        }

        // Render items
        for (i, item) in self.items.iter().take(area.height as usize - 2).enumerate() {
            let y = area.y + 2 + i as u16;

            // Status indicator
            let status_color = match item.status {
                ExecutionStatus::Pending => Color::Yellow,
                ExecutionStatus::Running => Color::Blue,
                ExecutionStatus::Success => Color::Green,
                ExecutionStatus::Failed => Color::Red,
                ExecutionStatus::Blocked => Color::Magenta,
            };

            let status_symbol = match item.status {
                ExecutionStatus::Pending => "○",
                ExecutionStatus::Running => "▶",
                ExecutionStatus::Success => "✓",
                ExecutionStatus::Failed => "✗",
                ExecutionStatus::Blocked => "◼",
            };

            buf.set_string(
                area.x + 2,
                y,
                status_symbol,
                Style::default().fg(status_color),
            );

            // Capability name
            let cap_text = format!("{}: {}", item.capability_name, item.execution_id);
            buf.set_string(area.x + 6, y, &cap_text, Style::default());

            // Actor
            let actor_text = format!("[{}]", item.actor);
            buf.set_string(area.x + 40, y, &actor_text, Style::default().dim());

            // Risk score if present
            if let Some(score) = item.risk_score {
                let risk_text = format!(" Risk: {:.2}", score);
                let risk_color = if score > 0.7 {
                    Color::Red
                } else if score > 0.4 {
                    Color::Yellow
                } else {
                    Color::Green
                };
                buf.set_string(area.x + 55, y, &risk_text, Style::default().fg(risk_color));
            }
        }
    }
}

/// Approval Queue View
pub struct ApprovalQueueView {
    approvals: Vec<ApprovalItem>,
    selected: usize,
}

#[derive(Debug, Clone)]
pub struct ApprovalItem {
    pub approval_id: String,
    pub capability_name: String,
    pub requester: String,
    pub requested_at: String,
    pub blast_radius: Option<String>,
    pub requires_human: bool,
}

impl ApprovalQueueView {
    pub fn new() -> Self {
        Self {
            approvals: Vec::new(),
            selected: 0,
        }
    }

    pub fn add_approval(&mut self, approval: ApprovalItem) {
        self.approvals.push(approval);
    }

    pub fn approve(&mut self, index: usize) -> Option<ApprovalItem> {
        if index < self.approvals.len() {
            Some(self.approvals.remove(index))
        } else {
            None
        }
    }

    pub fn deny(&mut self, index: usize) -> Option<ApprovalItem> {
        self.approve(index)
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let title = " Approval Queue ";
        buf.set_string(area.x, area.y, title, Style::default().bold());

        if self.approvals.is_empty() {
            buf.set_string(
                area.x + 2,
                area.y + 2,
                "No pending approvals",
                Style::default().dim(),
            );
            return;
        }

        for (i, approval) in self
            .approvals
            .iter()
            .take(area.height as usize - 2)
            .enumerate()
        {
            let y = area.y + 2 + i as u16;
            let selected = i == self.selected;

            let prefix = if selected { "▶" } else { " " };
            buf.set_string(area.x + 2, y, prefix, Style::default().fg(Color::Yellow));

            let cap_text = format!(
                "{} requested by {}",
                approval.capability_name, approval.requester
            );
            buf.set_string(area.x + 5, y, &cap_text, Style::default());

            if approval.requires_human {
                buf.set_string(
                    area.x + 50,
                    y,
                    "[HUMAN REQUIRED]",
                    Style::default().fg(Color::Red).bold(),
                );
            }

            if let Some(radius) = &approval.blast_radius {
                let radius_text = format!(" Blast: {}", radius);
                buf.set_string(area.x + 70, y, &radius_text, Style::default().dim());
            }
        }
    }

    pub fn move_selection(&mut self, delta: isize) {
        let new_selected =
            (self.selected as isize + delta).clamp(0, self.approvals.len() as isize - 1) as usize;
        self.selected = new_selected;
    }
}

impl Default for ApprovalQueueView {
    fn default() -> Self {
        Self::new()
    }
}

/// Replay Debugger View
pub struct ReplayDebuggerView {
    session_id: String,
    events: Vec<ReplayEvent>,
    current_index: usize,
}

#[derive(Debug, Clone)]
pub struct ReplayEvent {
    pub event_id: String,
    pub timestamp: String,
    pub event_type: String,
    pub description: String,
    pub payload: String,
}

impl ReplayDebuggerView {
    pub fn new(session_id: String) -> Self {
        Self {
            session_id,
            events: Vec::new(),
            current_index: 0,
        }
    }

    pub fn add_event(&mut self, event: ReplayEvent) {
        self.events.push(event);
    }

    pub fn step_forward(&mut self) {
        if self.current_index < self.events.len() - 1 {
            self.current_index += 1;
        }
    }

    pub fn step_back(&mut self) {
        if self.current_index > 0 {
            self.current_index -= 1;
        }
    }

    pub fn jump_to_start(&mut self) {
        self.current_index = 0;
    }

    pub fn jump_to_end(&mut self) {
        self.current_index = self.events.len().saturating_sub(1);
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let title = format!(" Replay: {} ", self.session_id);
        buf.set_string(area.x, area.y, &title, Style::default().bold());

        // Timeline
        let timeline = format!("[{}/{}]", self.current_index + 1, self.events.len());
        let timeline_x = area.x + area.width as usize - timeline.len() - 2;
        buf.set_string(timeline_x as u16, area.y, &timeline, Style::default().dim());

        if self.events.is_empty() {
            buf.set_string(
                area.x + 2,
                area.y + 2,
                "No events to replay",
                Style::default().dim(),
            );
            return;
        }

        // Current event details
        let event = &self.events[self.current_index];

        buf.set_string(
            area.x + 2,
            area.y + 2,
            &format!("Event: {}", event.event_type),
            Style::default().bold(),
        );
        buf.set_string(
            area.x + 2,
            area.y + 3,
            &format!("Time: {}", event.timestamp),
            Style::default().dim(),
        );
        buf.set_string(
            area.x + 2,
            area.y + 4,
            &format!("ID: {}", event.event_id),
            Style::default().dim(),
        );

        // Description
        let desc_area = Rect::new(
            area.x + 2,
            area.y + 6,
            area.x + area.width - 2,
            area.y + area.height - 2,
        );
        buf.set_string(
            desc_area.x,
            desc_area.y,
            &event.description,
            Style::default(),
        );

        // Payload preview
        if event.payload.len() > 50 {
            let preview = format!("Payload: {}...", &event.payload[..50]);
            buf.set_string(
                desc_area.x,
                desc_area.y + 1,
                &preview,
                Style::default().dim(),
            );
        } else {
            let preview = format!("Payload: {}", event.payload);
            buf.set_string(
                desc_area.x,
                desc_area.y + 1,
                &preview,
                Style::default().dim(),
            );
        }
    }
}

/// Risk Visualization View
pub struct RiskVisualizationView {
    executions: Vec<RiskExecution>,
}

#[derive(Debug, Clone)]
pub struct RiskExecution {
    pub execution_id: String,
    pub capability_name: String,
    pub financial_risk: f32,
    pub irreversibility_risk: f32,
    pub privacy_risk: f32,
    pub overall_risk: f32,
}

impl RiskVisualizationView {
    pub fn new() -> Self {
        Self {
            executions: Vec::new(),
        }
    }

    pub fn add_execution(&mut self, execution: RiskExecution) {
        self.executions.push(execution);
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let title = " Risk Visualization ";
        buf.set_string(area.x, area.y, title, Style::default().bold());

        if self.executions.isEmpty() {
            buf.set_string(
                area.x + 2,
                area.y + 2,
                "No risk data",
                Style::default().dim(),
            );
            return;
        }

        // Header
        buf.set_string(
            area.x + 2,
            area.y + 2,
            "Capability",
            Style::default().bold(),
        );
        buf.set_string(
            area.x + 30,
            area.y + 2,
            "Financial",
            Style::default().bold(),
        );
        buf.set_string(
            area.x + 42,
            area.y + 2,
            "Irrevers.",
            Style::default().bold(),
        );
        buf.set_string(area.x + 53, area.y + 2, "Privacy", Style::default().bold());
        buf.set_string(area.x + 63, area.y + 2, "Overall", Style::default().bold());

        for (i, exec) in self
            .executions
            .iter()
            .take(area.height as usize - 4)
            .enumerate()
        {
            let y = area.y + 3 + i as u16;

            // Capability name (truncated)
            let name = if exec.capability_name.len() > 25 {
                format!("{}...", &exec.capability_name[..22])
            } else {
                exec.capability_name.clone()
            };
            buf.set_string(area.x + 2, y, &name, Style::default());

            // Risk bars
            Self::render_risk_bar(area.x + 30, y, exec.financial_risk, buf);
            Self::render_risk_bar(area.x + 42, y, exec.irreversibility_risk, buf);
            Self::render_risk_bar(area.x + 53, y, exec.privacy_risk, buf);
            Self::render_risk_bar(area.x + 63, y, exec.overall_risk, buf);
        }
    }

    fn render_risk_bar(x: u16, y: u16, value: f32, buf: &mut Buffer) {
        let segments = (value * 10.0) as usize;
        let color = if value > 0.7 {
            Color::Red
        } else if value > 0.4 {
            Color::Yellow
        } else {
            Color::Green
        };

        for i in 0..10 {
            let ch = if i < segments { "█" } else { "░" };
            buf.set_string(x + i as u16, y, ch, Style::default().fg(color));
        }
    }
}

impl Default for RiskVisualizationView {
    fn default() -> Self {
        Self::new()
    }
}

/// Policy Editor View
pub struct PolicyEditorView {
    policies: Vec<PolicyItem>,
    selected: usize,
    editing: bool,
}

#[derive(Debug, Clone)]
pub struct PolicyItem {
    pub name: String,
    pub effect: PolicyEffect,
    pub capabilities: Vec<String>,
    pub conditions: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PolicyEffect {
    Allow,
    Deny,
    Ask,
}

impl PolicyEditorView {
    pub fn new() -> Self {
        Self {
            policies: Vec::new(),
            selected: 0,
            editing: false,
        }
    }

    pub fn add_policy(&mut self, policy: PolicyItem) {
        self.policies.push(policy);
    }

    pub fn toggle_edit(&mut self) {
        self.editing = !self.editing;
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let title = if self.editing {
            " Policy Editor [EDITING] "
        } else {
            " Policy Editor "
        };
        buf.set_string(area.x, area.y, title, Style::default().bold());

        if self.policies.isEmpty() {
            buf.set_string(
                area.x + 2,
                area.y + 2,
                "No policies defined",
                Style::default().dim(),
            );
            return;
        }

        for (i, policy) in self
            .policies
            .iter()
            .take(area.height as usize - 2)
            .enumerate()
        {
            let y = area.y + 2 + i as u16;
            let selected = i == self.selected;

            let prefix = if selected { "▶" } else { " " };
            let effect_str = match policy.effect {
                PolicyEffect::Allow => "[ALLOW]",
                PolicyEffect::Deny => "[DENY]",
                PolicyEffect::Ask => "[ASK ]",
            };
            let effect_color = match policy.effect {
                PolicyEffect::Allow => Color::Green,
                PolicyEffect::Deny => Color::Red,
                PolicyEffect::Ask => Color::Yellow,
            };

            buf.set_string(area.x + 2, y, prefix, Style::default());
            buf.set_string(area.x + 4, y, effect_str, Style::default().fg(effect_color));
            buf.set_string(area.x + 12, y, &policy.name, Style::default().bold());

            // Show first few capabilities
            if !policy.capabilities.isEmpty() {
                let caps_str = format!(
                    " ({})",
                    policy
                        .capabilities
                        .iter()
                        .take(2)
                        .collect::<Vec<_>>()
                        .join(", ")
                );
                buf.set_string(area.x + 40, y, &caps_str, Style::default().dim());
            }
        }
    }

    pub fn move_selection(&mut self, delta: isize) {
        let new_selected =
            (self.selected as isize + delta).clamp(0, self.policies.len() as isize - 1) as usize;
        self.selected = new_selected;
    }
}

impl Default for PolicyEditorView {
    fn default() -> Self {
        Self::new()
    }
}

/// Main Supervision Dashboard combining all views
pub struct SupervisionDashboard {
    pub live_feed: LiveFeedView,
    pub approval_queue: ApprovalQueueView,
    pub replay: Option<ReplayDebuggerView>,
    pub risk_viz: RiskVisualizationView,
    pub policy_editor: PolicyEditorView,
    active_view: DashboardView,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DashboardView {
    LiveFeed,
    Approvals,
    Replay,
    Risk,
    Policy,
}

impl SupervisionDashboard {
    pub fn new() -> Self {
        Self {
            live_feed: LiveFeedView::new(50),
            approval_queue: ApprovalQueueView::new(),
            replay: None,
            risk_viz: RiskVisualizationView::new(),
            policy_editor: PolicyEditorView::new(),
            active_view: DashboardView::LiveFeed,
        }
    }

    pub fn set_active_view(&mut self, view: DashboardView) {
        self.active_view = view;
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        match self.active_view {
            DashboardView::LiveFeed => self.live_feed.render(area, buf),
            DashboardView::Approvals => self.approval_queue.render(area, buf),
            DashboardView::Replay => {
                if let Some(replay) = &self.replay {
                    replay.render(area, buf);
                } else {
                    buf.set_string(
                        area.x + 2,
                        area.y + 2,
                        "No session selected for replay",
                        Style::default().dim(),
                    );
                }
            }
            DashboardView::Risk => self.risk_viz.render(area, buf),
            DashboardView::Policy => self.policy_editor.render(area, buf),
        }
    }

    pub fn switch_view(&mut self) {
        self.active_view = match self.active_view {
            DashboardView::LiveFeed => DashboardView::Approvals,
            DashboardView::Approvals => DashboardView::Replay,
            DashboardView::Replay => DashboardView::Risk,
            DashboardView::Risk => DashboardView::Policy,
            DashboardView::Policy => DashboardView::LiveFeed,
        };
    }
}

impl Default for SupervisionDashboard {
    fn default() -> Self {
        Self::new()
    }
}
