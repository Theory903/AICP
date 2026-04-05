use ratatui::style::Style;
use ratatui::widgets::Block;

pub struct ThemedBox {
    block: Block<'static>,
}

impl ThemedBox {
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
        self.block = self.block.border_style(Style::default());
        self
    }

    pub fn style(mut self, style: Style) -> Self {
        self.block = self.block.style(style);
        self
    }
}

impl Default for ThemedBox {
    fn default() -> Self {
        Self::new()
    }
}
