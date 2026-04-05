use crate::design_system::ThemedText;
use ratatui::prelude::*;

pub struct AgentList {
    agents: Vec<Agent>,
    selected: usize,
}

#[derive(Debug, Clone)]
pub struct Agent {
    pub name: String,
    pub status: String,
    pub model: String,
}

impl AgentList {
    pub fn new(agents: Vec<Agent>) -> Self {
        Self {
            agents,
            selected: 0,
        }
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        for (i, agent) in self.agents.iter().enumerate() {
            let style = if i == self.selected {
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default()
            };

            let line = format!("{} - {}", agent.name, agent.status);
            buf.set_string(area.x, area.y + i as u16, line, style);
        }
    }

    pub fn select_next(&mut self) {
        if self.selected < self.agents.len() - 1 {
            self.selected += 1;
        }
    }

    pub fn select_previous(&mut self) {
        if self.selected > 0 {
            self.selected -= 1;
        }
    }
}
