use ratatui::prelude::*;

pub struct SettingsPanel {
    tabs: Vec<SettingsTab>,
    active_tab: usize,
}

#[derive(Debug, Clone)]
pub enum SettingsTab {
    General,
    Providers,
    Appearance,
    Security,
    Advanced,
}

impl SettingsPanel {
    pub fn new() -> Self {
        Self {
            tabs: vec![
                SettingsTab::General,
                SettingsTab::Providers,
                SettingsTab::Appearance,
                SettingsTab::Security,
                SettingsTab::Advanced,
            ],
            active_tab: 0,
        }
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let tabs_str = self
            .tabs
            .iter()
            .enumerate()
            .map(|(i, tab)| {
                if i == self.active_tab {
                    format!("[{:?}]", tab)
                } else {
                    format!(" {:?} ", tab)
                }
            })
            .collect::<Vec<_>>()
            .join(" ");

        buf.set_string(area.x, area.y, tabs_str, Style::default().fg(Color::Cyan));
    }

    pub fn select_next(&mut self) {
        if self.active_tab < self.tabs.len() - 1 {
            self.active_tab += 1;
        }
    }

    pub fn select_previous(&mut self) {
        if self.active_tab > 0 {
            self.active_tab -= 1;
        }
    }
}

impl Default for SettingsPanel {
    fn default() -> Self {
        Self::new()
    }
}
