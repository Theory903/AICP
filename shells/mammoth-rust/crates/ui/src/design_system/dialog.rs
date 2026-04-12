use ratatui::style::Style;
use ratatui::widgets::Block;

pub struct Dialog {
    title: Option<String>,
    body: String,
}

impl Dialog {
    pub fn new(title: impl Into<String>, body: impl Into<String>) -> Self {
        Self {
            title: Some(title.into()),
            body: body.into(),
        }
    }

    pub fn title(&self) -> Option<&str> {
        self.title.as_deref()
    }

    pub fn body(&self) -> &str {
        &self.body
    }
}
