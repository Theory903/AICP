use crate::nl_workflow::WorkflowSpec;
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    layout::Rect,
    style::{Color, Style},
    text::Line,
    widgets::{Block, Borders, Paragraph},
    Frame,
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FlowBuilderAction {
    None,
    AddStep,
    DeleteStep { step_id: String },
    Close,
}

pub struct FlowBuilderOverlay {
    spec: WorkflowSpec,
    selected_idx: usize,
}

impl FlowBuilderOverlay {
    #[must_use]
    pub fn new(spec: WorkflowSpec) -> Self {
        Self {
            spec,
            selected_idx: 0,
        }
    }

    pub fn render(&mut self, frame: &mut Frame, area: Rect) {
        let step_count = self.spec.steps.len();
        if step_count == 0 {
            let p = Paragraph::new("No steps. Press 'a' to add.")
                .block(Block::default().borders(Borders::ALL).title("Flow Builder"));
            frame.render_widget(p, area);
            return;
        }

        let cell_height = 3u16;
        let arrow_height = 1u16;
        let mut y = area.y;
        for (i, step) in self.spec.steps.iter().enumerate() {
            if y + cell_height > area.y + area.height {
                break;
            }
            let style = if i == self.selected_idx {
                Style::default().fg(Color::Yellow)
            } else {
                Style::default()
            };
            let label = step.capability_name.as_deref().unwrap_or(&step.step_type);
            let p = Paragraph::new(Line::from(format!("[{}] {}", step.id, label)))
                .style(style)
                .block(Block::default().borders(Borders::ALL));
            frame.render_widget(
                p,
                Rect {
                    x: area.x,
                    y,
                    width: area.width,
                    height: cell_height,
                },
            );
            y += cell_height;
            if i < step_count - 1 {
                if y < area.y + area.height {
                    let arrow = Paragraph::new("   ↓");
                    frame.render_widget(
                        arrow,
                        Rect {
                            x: area.x,
                            y,
                            width: area.width,
                            height: arrow_height,
                        },
                    );
                    y += arrow_height;
                }
            }
        }
    }

    pub fn handle_event(&mut self, key: KeyEvent) -> FlowBuilderAction {
        match key.code {
            KeyCode::Esc => FlowBuilderAction::Close,
            KeyCode::Char('a') => FlowBuilderAction::AddStep,
            KeyCode::Char('d') => {
                if let Some(step) = self.spec.steps.get(self.selected_idx) {
                    FlowBuilderAction::DeleteStep {
                        step_id: step.id.clone(),
                    }
                } else {
                    FlowBuilderAction::None
                }
            }
            KeyCode::Down => {
                self.selected_idx =
                    (self.selected_idx + 1).min(self.spec.steps.len().saturating_sub(1));
                FlowBuilderAction::None
            }
            KeyCode::Up => {
                self.selected_idx = self.selected_idx.saturating_sub(1);
                FlowBuilderAction::None
            }
            _ => FlowBuilderAction::None,
        }
    }
}
