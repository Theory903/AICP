use super::color::ColorPalette;

pub struct Theme {
    pub colors: ColorPalette,
    pub name: String,
}

impl Default for Theme {
    fn default() -> Self {
        Self {
            colors: ColorPalette::default(),
            name: "default".to_string(),
        }
    }
}

impl Theme {
    pub fn primary(&self) -> Option<ratatui::style::Color> {
        Some(self.colors.primary)
    }
}
