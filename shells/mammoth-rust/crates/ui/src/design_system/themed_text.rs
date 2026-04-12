use ratatui::style::Style;

pub struct ThemedText {
    content: String,
    style: Style,
}

impl ThemedText {
    pub fn new(content: &str) -> Self {
        Self {
            content: content.to_string(),
            style: Style::default(),
        }
    }

    pub fn theme(mut self, theme: &super::Theme) -> Self {
        self.style = self.style.fg(theme.colors.foreground);
        self
    }

    pub fn content(&self) -> &str {
        &self.content
    }
}
