use ratatui::prelude::*;
use ratatui::widgets::{Block, Borders};

pub struct DiffView {
    additions: u32,
    deletions: u32,
    hunks: Vec<DiffHunk>,
}

#[derive(Debug, Clone)]
pub struct DiffHunk {
    pub old_start: u32,
    pub new_start: u32,
    pub lines: Vec<DiffLine>,
}

#[derive(Debug, Clone)]
pub enum DiffLine {
    Context(String),
    Addition(String),
    Deletion(String),
}

impl DiffView {
    pub fn new() -> Self {
        Self {
            additions: 0,
            deletions: 0,
            hunks: Vec::new(),
        }
    }

    pub fn add_hunk(&mut self, hunk: DiffHunk) {
        for line in &hunk.lines {
            match line {
                DiffLine::Addition(_) => self.additions += 1,
                DiffLine::Deletion(_) => self.deletions += 1,
                DiffLine::Context(_) => {}
            }
        }
        self.hunks.push(hunk);
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let block = Block::default()
            .title(format!("Diff +{} -{}", self.additions, self.deletions))
            .borders(Borders::ALL);
        buf.set_widget(area, block);

        let inner = block.inner(area);
        let mut y = inner.y;

        for hunk in &self.hunks {
            for line in &hunk.lines {
                if y >= inner.bottom() {
                    break;
                }
                let (text, style) = match line {
                    DiffLine::Addition(s) => (s.as_str(), Style::default().fg(Color::Green)),
                    DiffLine::Deletion(s) => (s.as_str(), Style::default().fg(Color::Red)),
                    DiffLine::Context(s) => (s.as_str(), Style::default()),
                };
                buf.set_string(inner.x, y, text, style);
                y += 1;
            }
        }
    }
}

impl Default for DiffView {
    fn default() -> Self {
        Self::new()
    }
}
