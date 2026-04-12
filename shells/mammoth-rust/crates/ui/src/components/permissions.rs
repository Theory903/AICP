use crate::design_system::Dialog;
use ratatui::prelude::*;

pub struct PermissionRequest {
    tool_name: String,
    description: String,
    is_dangerous: bool,
}

impl PermissionRequest {
    pub fn new(tool_name: String, description: String, is_dangerous: bool) -> Self {
        Self {
            tool_name,
            description,
            is_dangerous,
        }
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let dialog = Dialog::new("Permission Required", &self.description);

        let title = format!("Permission: {}", self.tool_name);
        buf.set_string(
            area.x,
            area.y,
            title,
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        );

        buf.set_string(area.x, area.y + 2, &self.description, Style::default());

        if self.is_dangerous {
            let warning = "⚠️ This action may have side effects";
            buf.set_string(
                area.x,
                area.y + 5,
                warning,
                Style::default().fg(Color::Yellow),
            );
        }

        buf.set_string(
            area.x,
            area.y + 7,
            "Press [y] to allow, [n] to deny",
            Style::default().fg(Color::White),
        );
    }
}
