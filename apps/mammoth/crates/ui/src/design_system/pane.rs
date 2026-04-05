use ratatui::style::Style;
use ratatui::widgets::Block;

pub struct Pane {
    block: Block<'static>,
}

impl Pane {
    pub fn new() -> Self {
        Self {
            block: Block::default(),
        }
    }

    pub fn title(mut self, title: String) -> Self {
        self.block = self.block.title(title);
        self
    }

    pub fn bordered(mut self) -> Self {
        self.block = self.block.borders(ratatui::widgets::Borders::ALL);
        self
    }

    pub fn style(mut self, style: Style) -> Self {
        self.block = self.block.style(style);
        self
    }
}

impl Default for Pane {
    fn default() -> Self {
        Self::new()
    }
}
