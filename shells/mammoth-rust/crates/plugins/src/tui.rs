use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    layout::{Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    text::Line,
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph},
    Frame,
};

use crate::registry::PluginListing;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MarketplaceAction {
    None,
    Install { id: String },
    Update { id: String },
    Remove { id: String },
    Close,
}

pub struct MarketplaceOverlay {
    listings: Vec<PluginListing>,
    list_state: ListState,
}

impl MarketplaceOverlay {
    #[must_use]
    pub fn new(listings: Vec<PluginListing>) -> Self {
        let mut list_state = ListState::default();
        if !listings.is_empty() {
            list_state.select(Some(0));
        }
        Self {
            listings,
            list_state,
        }
    }

    pub fn render(&mut self, frame: &mut Frame, area: ratatui::layout::Rect) {
        let chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
            .split(area);

        let items: Vec<ListItem> = self
            .listings
            .iter()
            .map(|l| ListItem::new(Line::from(format!("{} v{}", l.name, l.latest_version))))
            .collect();
        let list = List::new(items)
            .block(Block::default().borders(Borders::ALL).title("Plugins"))
            .highlight_style(
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            );
        frame.render_stateful_widget(list, chunks[0], &mut self.list_state);

        let detail = if let Some(idx) = self.list_state.selected() {
            let l = &self.listings[idx];
            format!(
                "{}\n\nVersion: {}\n{}",
                l.name, l.latest_version, l.description
            )
        } else {
            "Select a plugin".to_string()
        };
        let para =
            Paragraph::new(detail).block(Block::default().borders(Borders::ALL).title("Details"));
        frame.render_widget(para, chunks[1]);
    }

    pub fn handle_event(&mut self, key: KeyEvent) -> MarketplaceAction {
        match key.code {
            KeyCode::Esc => MarketplaceAction::Close,
            KeyCode::Down => {
                let next = self
                    .list_state
                    .selected()
                    .map_or(0, |i| (i + 1).min(self.listings.len().saturating_sub(1)));
                self.list_state.select(Some(next));
                MarketplaceAction::None
            }
            KeyCode::Up => {
                let prev = self
                    .list_state
                    .selected()
                    .map_or(0, |i| i.saturating_sub(1));
                self.list_state.select(Some(prev));
                MarketplaceAction::None
            }
            KeyCode::Enter => {
                if let Some(idx) = self.list_state.selected() {
                    MarketplaceAction::Install {
                        id: self.listings[idx].id.clone(),
                    }
                } else {
                    MarketplaceAction::None
                }
            }
            KeyCode::Char('u') => {
                if let Some(idx) = self.list_state.selected() {
                    MarketplaceAction::Update {
                        id: self.listings[idx].id.clone(),
                    }
                } else {
                    MarketplaceAction::None
                }
            }
            KeyCode::Char('d') => {
                if let Some(idx) = self.list_state.selected() {
                    MarketplaceAction::Remove {
                        id: self.listings[idx].id.clone(),
                    }
                } else {
                    MarketplaceAction::None
                }
            }
            _ => MarketplaceAction::None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crossterm::event::KeyModifiers;

    fn key(code: KeyCode) -> KeyEvent {
        KeyEvent::new(code, KeyModifiers::NONE)
    }

    fn make_listing(id: &str) -> PluginListing {
        PluginListing {
            id: id.to_string(),
            name: id.to_string(),
            description: "desc".to_string(),
            latest_version: "1.0".to_string(),
            download_url: format!("https://example.com/{id}.tar.gz"),
            signature_url: format!("https://example.com/{id}.sig"),
            publisher_key_url: "https://example.com/key.pub".to_string(),
        }
    }

    #[test]
    fn escape_returns_close_action() {
        let mut overlay = MarketplaceOverlay::new(vec![]);
        assert_eq!(
            overlay.handle_event(key(KeyCode::Esc)),
            MarketplaceAction::Close
        );
    }

    #[test]
    fn enter_returns_install_with_id() {
        let mut overlay = MarketplaceOverlay::new(vec![make_listing("foo")]);
        assert_eq!(
            overlay.handle_event(key(KeyCode::Enter)),
            MarketplaceAction::Install {
                id: "foo".to_string()
            }
        );
    }

    #[test]
    fn u_key_returns_update_action() {
        let mut overlay = MarketplaceOverlay::new(vec![make_listing("bar")]);
        assert_eq!(
            overlay.handle_event(key(KeyCode::Char('u'))),
            MarketplaceAction::Update {
                id: "bar".to_string()
            }
        );
    }

    #[test]
    fn d_key_returns_remove_action() {
        let mut overlay = MarketplaceOverlay::new(vec![make_listing("baz")]);
        assert_eq!(
            overlay.handle_event(key(KeyCode::Char('d'))),
            MarketplaceAction::Remove {
                id: "baz".to_string()
            }
        );
    }

    #[test]
    fn empty_overlay_enter_returns_none() {
        let mut overlay = MarketplaceOverlay::new(vec![]);
        assert_eq!(
            overlay.handle_event(key(KeyCode::Enter)),
            MarketplaceAction::None
        );
    }
}
