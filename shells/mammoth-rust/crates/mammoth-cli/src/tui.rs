use std::time::Duration;

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style, Stylize};
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph, Tabs, Wrap};
use ratatui::{DefaultTerminal, Frame};

use super::{
    collect_tool_results, collect_tool_uses, status_context, truncate_for_prompt, LiveCli,
    MAMMOTH_MARK,
};
use commands::{slash_command_specs, SlashCommand, SlashCommandSpec};
use mammoth_runtime::{ContentBlock, ConversationMessage, MessageRole};

pub(super) fn run_app(cli: LiveCli) -> Result<(), Box<dyn std::error::Error>> {
    let mut terminal = ratatui::init();
    let result = MammothTui::new(cli)?.run(&mut terminal);
    ratatui::restore();
    result
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum InspectorTab {
    Status,
    Diff,
    Tools,
}

impl InspectorTab {
    const ALL: [Self; 3] = [Self::Status, Self::Diff, Self::Tools];

    fn title(self) -> &'static str {
        match self {
            Self::Status => "Status",
            Self::Diff => "Diff",
            Self::Tools => "Tools",
        }
    }

    fn next(self) -> Self {
        match self {
            Self::Status => Self::Diff,
            Self::Diff => Self::Tools,
            Self::Tools => Self::Status,
        }
    }

    fn previous(self) -> Self {
        match self {
            Self::Status => Self::Tools,
            Self::Diff => Self::Status,
            Self::Tools => Self::Diff,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct UiNote {
    title: String,
    body: String,
    kind: UiNoteKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum UiNoteKind {
    Info,
    Error,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
struct Composer {
    text: String,
    cursor: usize,
}

impl Composer {
    fn take(&mut self) -> String {
        self.cursor = 0;
        std::mem::take(&mut self.text)
    }

    fn replace(&mut self, value: impl Into<String>) {
        self.text = value.into();
        self.cursor = self.text.len();
    }

    fn insert_char(&mut self, ch: char) {
        self.text.insert(self.cursor, ch);
        self.cursor += ch.len_utf8();
    }

    fn insert_newline(&mut self) {
        self.insert_char('\n');
    }

    fn backspace(&mut self) {
        if self.cursor == 0 {
            return;
        }
        let previous = previous_boundary(&self.text, self.cursor);
        self.text.drain(previous..self.cursor);
        self.cursor = previous;
    }

    fn delete(&mut self) {
        if self.cursor >= self.text.len() {
            return;
        }
        let next = next_boundary(&self.text, self.cursor);
        self.text.drain(self.cursor..next);
    }

    fn move_left(&mut self) {
        self.cursor = previous_boundary(&self.text, self.cursor);
    }

    fn move_right(&mut self) {
        self.cursor = next_boundary(&self.text, self.cursor);
    }

    fn move_home(&mut self) {
        self.cursor = line_start(&self.text, self.cursor);
    }

    fn move_end(&mut self) {
        self.cursor = line_end(&self.text, self.cursor);
    }

    fn cursor_row_col(&self) -> (u16, u16) {
        let prefix = &self.text[..self.cursor];
        let row =
            u16::try_from(prefix.bytes().filter(|byte| *byte == b'\n').count()).unwrap_or(u16::MAX);
        let col = u16::try_from(
            prefix
                .rsplit_once('\n')
                .map_or(prefix.chars().count(), |(_, suffix)| suffix.chars().count()),
        )
        .unwrap_or(u16::MAX);
        (row, col)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct PaletteState {
    query: String,
    selected: usize,
}

impl PaletteState {
    fn new(query: String) -> Self {
        Self { query, selected: 0 }
    }

    fn filtered_specs(&self) -> Vec<&'static SlashCommandSpec> {
        let query = self
            .query
            .trim()
            .trim_start_matches('/')
            .to_ascii_lowercase();
        let mut matches = slash_command_specs()
            .iter()
            .filter(|spec| {
                query.is_empty()
                    || spec.name.contains(&query)
                    || spec.summary.to_ascii_lowercase().contains(&query)
            })
            .collect::<Vec<_>>();
        matches.sort_by_key(|spec| spec.name);
        matches
    }

    fn move_down(&mut self) {
        let len = self.filtered_specs().len();
        if len == 0 {
            self.selected = 0;
            return;
        }
        self.selected = (self.selected + 1) % len;
    }

    fn move_up(&mut self) {
        let len = self.filtered_specs().len();
        if len == 0 {
            self.selected = 0;
            return;
        }
        self.selected = if self.selected == 0 {
            len - 1
        } else {
            self.selected - 1
        };
    }

    fn selected_spec(&self) -> Option<&'static SlashCommandSpec> {
        self.filtered_specs().get(self.selected).copied()
    }
}

struct MammothTui {
    cli: LiveCli,
    composer: Composer,
    inspector: InspectorTab,
    transcript_scroll: u16,
    palette: Option<PaletteState>,
    notes: Vec<UiNote>,
    status_cache: String,
    diff_cache: String,
    tool_cache: String,
    should_quit: bool,
    footer_message: String,
}

impl MammothTui {
    fn new(cli: LiveCli) -> Result<Self, Box<dyn std::error::Error>> {
        let status_cache = cli.status_report();
        let diff_cache = LiveCli::diff_report().unwrap_or_else(|error| error.to_string());
        let tool_cache = "No tool activity yet.

Run a prompt that uses tools or execute /debug-tool-call after a turn."
            .to_string();
        let footer_message =
            "Ctrl-P palette · Tab inspector · Ctrl-J newline · Enter send · Ctrl-C quit"
                .to_string();
        cli.persist_session()?;
        Ok(Self {
            cli,
            composer: Composer::default(),
            inspector: InspectorTab::Status,
            transcript_scroll: 0,
            palette: None,
            notes: Vec::new(),
            status_cache,
            diff_cache,
            tool_cache,
            should_quit: false,
            footer_message,
        })
    }

    fn run(&mut self, terminal: &mut DefaultTerminal) -> Result<(), Box<dyn std::error::Error>> {
        while !self.should_quit {
            terminal.draw(|frame| self.render(frame))?;
            if event::poll(Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    if key.kind == KeyEventKind::Press {
                        self.handle_key(key)?;
                    }
                }
            }
        }
        self.cli.persist_session()?;
        Ok(())
    }

    fn render(&mut self, frame: &mut Frame) {
        let outer = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3),
                Constraint::Min(12),
                Constraint::Length(6),
                Constraint::Length(1),
            ])
            .split(frame.area());

        self.render_header(frame, outer[0]);
        self.render_body(frame, outer[1]);
        let input_area = self.render_input(frame, outer[2]);
        self.render_footer(frame, outer[3]);

        if self.palette.is_none() {
            let (row, col) = self.composer.cursor_row_col();
            let inner = shrink(input_area, 1);
            let cursor_x = inner
                .x
                .saturating_add(col.min(inner.width.saturating_sub(1)));
            let cursor_y = inner
                .y
                .saturating_add(row.min(inner.height.saturating_sub(1)));
            frame.set_cursor_position((cursor_x, cursor_y));
        } else {
            self.render_palette(frame);
        }
    }

    fn render_header(&self, frame: &mut Frame, area: Rect) {
        let header = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(58), Constraint::Percentage(42)])
            .split(area);

        let title = format!(
            "{MAMMOTH_MARK} Mammoth TUI · {}",
            status_context(Some(&self.cli.session.path))
                .ok()
                .and_then(|ctx| ctx.git_branch)
                .unwrap_or_else(|| "workspace".to_string())
        );
        frame.render_widget(
            Paragraph::new(title)
                .style(
                    Style::default()
                        .fg(Color::Cyan)
                        .add_modifier(Modifier::BOLD),
                )
                .block(Block::default().borders(Borders::ALL).title("Deck")),
            header[0],
        );

        let right = vec![
            Line::from(vec!["Model ".dark_gray(), self.cli.model.as_str().yellow()]),
            Line::from(vec![
                "Session ".dark_gray(),
                self.cli.session.id.as_str().green(),
                "  Permissions ".dark_gray(),
                self.cli.permission_mode.as_str().magenta(),
            ]),
        ];
        frame.render_widget(
            Paragraph::new(right).block(Block::default().borders(Borders::ALL).title("Runtime")),
            header[1],
        );
    }

    fn render_body(&mut self, frame: &mut Frame, area: Rect) {
        let columns = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Length(30),
                Constraint::Min(40),
                Constraint::Length(42),
            ])
            .split(area);

        self.render_sidebar(frame, columns[0]);
        self.render_transcript(frame, columns[1]);
        self.render_inspector(frame, columns[2]);
    }

    fn render_sidebar(&self, frame: &mut Frame, area: Rect) {
        let sections = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(10), Constraint::Min(8)])
            .split(area);

        let quick = Text::from(vec![
            Line::from("/help").yellow(),
            Line::from("/status").yellow(),
            Line::from("/diff").yellow(),
            Line::from("/model <name>").yellow(),
            Line::from("/permissions <mode>").yellow(),
            Line::from("/debug-tool-call").yellow(),
        ]);
        frame.render_widget(
            Paragraph::new(quick)
                .wrap(Wrap { trim: false })
                .block(Block::default().borders(Borders::ALL).title("Commands")),
            sections[0],
        );

        let session_lines = vec![
            Line::from(format!(
                "workspace: {}",
                std::env::current_dir().ok().map_or_else(
                    || "<unknown>".to_string(),
                    |path| path.display().to_string()
                )
            )),
            Line::from(format!(
                "messages: {}",
                self.cli.runtime.session().messages.len()
            )),
            Line::from(format!("turns: {}", self.cli.runtime.usage().turns())),
            Line::from(String::new()),
            Line::from("Palette").cyan().bold(),
            Line::from("  Ctrl-P to browse commands"),
            Line::from(String::new()),
            Line::from("Inspectors").cyan().bold(),
            Line::from("  Tab / Shift-Tab cycles"),
            Line::from("  F1 status  F2 diff  F3 tools"),
        ];
        frame.render_widget(
            Paragraph::new(session_lines)
                .wrap(Wrap { trim: false })
                .block(Block::default().borders(Borders::ALL).title("Session")),
            sections[1],
        );
    }

    fn render_transcript(&self, frame: &mut Frame, area: Rect) {
        let transcript = Paragraph::new(self.transcript_text())
            .block(Block::default().borders(Borders::ALL).title("Conversation"))
            .wrap(Wrap { trim: false })
            .scroll((self.transcript_scroll, 0));
        frame.render_widget(transcript, area);
    }

    fn render_inspector(&self, frame: &mut Frame, area: Rect) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Min(0)])
            .split(area);

        let titles = InspectorTab::ALL
            .iter()
            .map(|tab| Line::from(tab.title()))
            .collect::<Vec<_>>();
        let selected = InspectorTab::ALL
            .iter()
            .position(|tab| *tab == self.inspector)
            .unwrap_or(0);
        frame.render_widget(
            Tabs::new(titles)
                .select(selected)
                .block(Block::default().borders(Borders::ALL).title("Inspector"))
                .highlight_style(
                    Style::default()
                        .fg(Color::Yellow)
                        .add_modifier(Modifier::BOLD),
                ),
            chunks[0],
        );

        let body = match self.inspector {
            InspectorTab::Status => self.status_cache.clone(),
            InspectorTab::Diff => self.diff_cache.clone(),
            InspectorTab::Tools => self.tool_cache.clone(),
        };
        frame.render_widget(
            Paragraph::new(body).wrap(Wrap { trim: false }).block(
                Block::default()
                    .borders(Borders::ALL)
                    .title(self.inspector.title()),
            ),
            chunks[1],
        );
    }

    fn render_input(&self, frame: &mut Frame, area: Rect) -> Rect {
        let title = if self.composer.text.trim_start().starts_with('/') {
            "Command"
        } else {
            "Composer"
        };
        frame.render_widget(
            Paragraph::new(if self.composer.text.is_empty() {
                Text::from(vec![
                    Line::from("Type a prompt or slash command...").dark_gray()
                ])
            } else {
                Text::from(self.composer.text.clone())
            })
            .wrap(Wrap { trim: false })
            .block(Block::default().borders(Borders::ALL).title(title)),
            area,
        );
        area
    }

    fn render_footer(&self, frame: &mut Frame, area: Rect) {
        frame.render_widget(
            Paragraph::new(self.footer_message.clone()).style(Style::default().fg(Color::DarkGray)),
            area,
        );
    }

    fn render_palette(&self, frame: &mut Frame) {
        let Some(palette) = &self.palette else {
            return;
        };
        let popup = centered_rect(72, 62, frame.area());
        frame.render_widget(Clear, popup);

        let layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Min(0)])
            .split(popup);

        frame.render_widget(
            Paragraph::new(format!("Search: {}", palette.query)).block(
                Block::default()
                    .borders(Borders::ALL)
                    .title("Command Palette"),
            ),
            layout[0],
        );

        let specs = palette.filtered_specs();
        let items = specs
            .iter()
            .map(|spec| {
                let hint = spec.argument_hint.unwrap_or("");
                ListItem::new(vec![
                    Line::from(vec![
                        Span::styled(
                            format!("/{}", spec.name),
                            Style::default().fg(Color::Yellow),
                        ),
                        Span::raw(if hint.is_empty() {
                            String::new()
                        } else {
                            format!(" {hint}")
                        }),
                    ]),
                    Line::from(Span::styled(
                        spec.summary,
                        Style::default().fg(Color::DarkGray),
                    )),
                ])
            })
            .collect::<Vec<_>>();
        let mut state = ListState::default();
        if !items.is_empty() {
            state.select(Some(palette.selected.min(items.len().saturating_sub(1))));
        }

        frame.render_stateful_widget(
            List::new(items)
                .block(Block::default().borders(Borders::ALL).title("Commands"))
                .highlight_style(
                    Style::default()
                        .bg(Color::DarkGray)
                        .add_modifier(Modifier::BOLD),
                )
                .highlight_symbol("> "),
            layout[1],
            &mut state,
        );
    }

    fn transcript_text(&self) -> Text<'static> {
        let mut lines = Vec::new();
        for message in &self.cli.runtime.session().messages {
            lines.extend(render_message(message));
            lines.push(Line::from(String::new()));
        }
        for note in &self.notes {
            let color = match note.kind {
                UiNoteKind::Info => Color::Cyan,
                UiNoteKind::Error => Color::Red,
            };
            lines.push(Line::from(Span::styled(
                format!("system · {}", note.title),
                Style::default().fg(color).add_modifier(Modifier::BOLD),
            )));
            for line in note.body.lines() {
                lines.push(Line::from(line.to_string()));
            }
            lines.push(Line::from(String::new()));
        }
        Text::from(lines)
    }

    fn handle_key(&mut self, key: KeyEvent) -> Result<(), Box<dyn std::error::Error>> {
        if self.palette.is_some() {
            self.handle_palette_key(key);
            return Ok(());
        }

        match key.code {
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                if self.composer.text.is_empty() {
                    self.should_quit = true;
                } else {
                    self.composer = Composer::default();
                    self.footer_message = "Composer cleared".to_string();
                }
            }
            KeyCode::Char('p') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.open_palette();
            }
            KeyCode::Tab if key.modifiers.contains(KeyModifiers::SHIFT) => {
                self.inspector = self.inspector.previous();
                self.refresh_inspector()?;
            }
            KeyCode::Tab => {
                if self.composer.text.trim_start().starts_with('/') {
                    self.open_palette();
                } else {
                    self.inspector = self.inspector.next();
                    self.refresh_inspector()?;
                }
            }
            KeyCode::F(1) => {
                self.inspector = InspectorTab::Status;
                self.refresh_inspector()?;
            }
            KeyCode::F(2) => {
                self.inspector = InspectorTab::Diff;
                self.refresh_inspector()?;
            }
            KeyCode::F(3) => {
                self.inspector = InspectorTab::Tools;
            }
            KeyCode::PageUp => {
                self.transcript_scroll = self.transcript_scroll.saturating_sub(3);
            }
            KeyCode::PageDown => {
                self.transcript_scroll = self.transcript_scroll.saturating_add(3);
            }
            KeyCode::Enter if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.composer.insert_newline();
            }
            KeyCode::Enter => self.submit()?,
            KeyCode::Backspace => self.composer.backspace(),
            KeyCode::Delete => self.composer.delete(),
            KeyCode::Left => self.composer.move_left(),
            KeyCode::Right => self.composer.move_right(),
            KeyCode::Home => self.composer.move_home(),
            KeyCode::End => self.composer.move_end(),
            KeyCode::Esc => {
                self.composer = Composer::default();
                self.footer_message = "Composer cleared".to_string();
            }
            KeyCode::Char(ch) => {
                self.composer.insert_char(ch);
            }
            _ => {}
        }
        Ok(())
    }

    fn handle_palette_key(&mut self, key: KeyEvent) {
        let Some(palette) = self.palette.as_mut() else {
            return;
        };

        match key.code {
            KeyCode::Esc => self.palette = None,
            KeyCode::Up => palette.move_up(),
            KeyCode::Down => palette.move_down(),
            KeyCode::Backspace => {
                palette.query.pop();
                palette.selected = 0;
            }
            KeyCode::Enter => {
                if let Some(spec) = palette.selected_spec() {
                    let mut command = format!("/{}", spec.name);
                    if let Some(hint) = spec.argument_hint {
                        command.push(' ');
                        command.push_str(hint);
                    }
                    self.composer.replace(command);
                }
                self.palette = None;
            }
            KeyCode::Char(ch) => {
                palette.query.push(ch);
                palette.selected = 0;
            }
            _ => {}
        }
    }

    fn open_palette(&mut self) {
        let query = self
            .composer
            .text
            .trim()
            .strip_prefix('/')
            .unwrap_or_default()
            .to_string();
        self.palette = Some(PaletteState::new(query));
    }

    fn submit(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let submitted = self.composer.take();
        let trimmed = submitted.trim();
        if trimmed.is_empty() {
            return Ok(());
        }
        if matches!(trimmed, "/quit" | "/exit") {
            self.should_quit = true;
            return Ok(());
        }

        if let Some(command) = SlashCommand::parse(trimmed) {
            self.execute_command(command)?;
            return Ok(());
        }

        let summary = self.cli.run_turn_capture(trimmed)?;
        self.tool_cache = format_tool_panel(&summary);
        self.status_cache = self.cli.status_report();
        self.footer_message = format!(
            "Sent {} chars · {} iterations",
            trimmed.chars().count(),
            summary.iterations
        );
        if summary.assistant_messages.iter().any(|message| {
            message
                .blocks
                .iter()
                .any(|block| matches!(block, ContentBlock::ToolUse { .. }))
        }) {
            self.inspector = InspectorTab::Tools;
        }
        self.diff_cache = LiveCli::diff_report().unwrap_or_else(|error| error.to_string());
        Ok(())
    }

    fn execute_command(&mut self, command: SlashCommand) -> Result<(), Box<dyn std::error::Error>> {
        match command {
            SlashCommand::Help => self.push_info("help", LiveCli::help_report()),
            SlashCommand::Status => {
                self.status_cache = self.cli.status_report();
                self.inspector = InspectorTab::Status;
                self.push_info("status", self.status_cache.clone());
            }
            SlashCommand::Cost => self.push_info("cost", self.cli.cost_report()),
            SlashCommand::Diff => {
                self.diff_cache = LiveCli::diff_report()?;
                self.inspector = InspectorTab::Diff;
                self.push_info("diff", self.diff_cache.clone());
            }
            SlashCommand::Version => self.push_info("version", LiveCli::version_report()),
            SlashCommand::Config { section } => {
                self.push_info("config", LiveCli::config_report(section.as_deref())?);
            }
            SlashCommand::Memory => self.push_info("memory", LiveCli::memory_report()?),
            SlashCommand::Agents { args } => {
                self.push_info("agents", LiveCli::agents_report(args.as_deref())?);
            }
            SlashCommand::Skills { args } => {
                self.push_info("skills", LiveCli::skills_report(args.as_deref())?);
            }
            SlashCommand::Anthropic { action, target } => {
                self.push_info(
                    "anthropic",
                    LiveCli::anthropic_report(action.as_deref(), target.as_deref())?,
                );
            }
            SlashCommand::GitHub { action, target } => {
                self.push_info(
                    "github",
                    LiveCli::github_report(action.as_deref(), target.as_deref())?,
                );
            }
            SlashCommand::Teleport { target } => {
                self.push_info("teleport", LiveCli::teleport_report(target.as_deref())?);
            }
            SlashCommand::DebugToolCall => {
                self.tool_cache = self.cli.debug_tool_call_report()?;
                self.inspector = InspectorTab::Tools;
                self.push_info("debug-tool-call", self.tool_cache.clone());
            }
            SlashCommand::Model { model } => {
                let report = self.cli.set_model_report(model)?;
                self.push_info("model", report);
                self.status_cache = self.cli.status_report();
            }
            SlashCommand::Permissions { mode } => {
                let report = self.cli.set_permissions_report(mode)?;
                self.push_info("permissions", report);
                self.status_cache = self.cli.status_report();
            }
            SlashCommand::Clear { confirm } => {
                let report = self.cli.clear_session_report(confirm)?;
                self.push_info("clear", report);
                self.status_cache = self.cli.status_report();
                self.tool_cache = "No tool activity yet.".to_string();
            }
            SlashCommand::Compact => {
                let report = self.cli.compact_report_string()?;
                self.push_info("compact", report);
                self.status_cache = self.cli.status_report();
            }
            SlashCommand::Bughunter { scope } => {
                let scope = scope.unwrap_or_else(|| "the current repository".to_string());
                let prompt = format!(
                    "You are /bughunter. Inspect {scope} and identify the most likely bugs or correctness issues. Prioritize concrete findings with file paths, severity, and suggested fixes. Use tools if needed."
                );
                let response = self.cli.run_internal_prompt_text(&prompt, true)?;
                self.push_info("bughunter", response);
            }
            SlashCommand::Ultraplan { task } => {
                let task = task.unwrap_or_else(|| "the current repo work".to_string());
                let prompt = format!(
                    "You are /ultraplan. Produce a deep multi-step execution plan for {task}. Include goals, risks, implementation sequence, verification steps, and rollback considerations. Use tools if needed."
                );
                let response = self.cli.run_internal_prompt_text(&prompt, true)?;
                self.push_info("ultraplan", response);
            }
            SlashCommand::Session { action, target } => {
                let (report, should_reload) = self
                    .cli
                    .session_command_report(action.as_deref(), target.as_deref())?;
                self.push_info("session", report);
                if should_reload {
                    self.status_cache = self.cli.status_report();
                }
            }
            SlashCommand::Plugins { action, target } => {
                let (report, should_reload) = self
                    .cli
                    .plugins_command_report(action.as_deref(), target.as_deref())?;
                self.push_info("plugins", report);
                if should_reload {
                    self.status_cache = self.cli.status_report();
                }
            }
            SlashCommand::Unknown(name) => {
                self.push_error("unknown-command", format!("unknown slash command: /{name}"));
            }
            other => {
                self.push_error(
                    "unsupported",
                    format!(
                        "{} is not wired into the TUI yet. Use the one-shot command or legacy line REPL path for this action.",
                        command_label(&other)
                    ),
                );
            }
        }
        Ok(())
    }

    fn refresh_inspector(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        match self.inspector {
            InspectorTab::Status => self.status_cache = self.cli.status_report(),
            InspectorTab::Diff => self.diff_cache = LiveCli::diff_report()?,
            InspectorTab::Tools => {}
        }
        Ok(())
    }

    fn push_info(&mut self, title: &str, body: String) {
        self.notes.push(UiNote {
            title: title.to_string(),
            body,
            kind: UiNoteKind::Info,
        });
        self.footer_message = format!("{title} updated");
    }

    fn push_error(&mut self, title: &str, body: String) {
        self.notes.push(UiNote {
            title: title.to_string(),
            body,
            kind: UiNoteKind::Error,
        });
        self.footer_message = format!("{title} failed");
    }
}

fn render_message(message: &ConversationMessage) -> Vec<Line<'static>> {
    let (label, color) = match message.role {
        MessageRole::System => ("system", Color::Cyan),
        MessageRole::User => ("you", Color::Yellow),
        MessageRole::Assistant => ("mammoth", Color::Green),
        MessageRole::Tool => ("tool", Color::Magenta),
    };

    let mut lines = vec![Line::from(Span::styled(
        label.to_string(),
        Style::default().fg(color).add_modifier(Modifier::BOLD),
    ))];
    for block in &message.blocks {
        match block {
            ContentBlock::Text { text } => {
                for line in text.lines() {
                    lines.push(Line::from(line.to_string()));
                }
            }
            ContentBlock::ToolUse { name, input, .. } => {
                lines.push(Line::from(format!("tool call · {name}")));
                if !input.is_empty() {
                    lines.push(Line::from(truncate_for_prompt(input, 600)));
                }
            }
            ContentBlock::ToolResult {
                tool_name,
                output,
                is_error,
                ..
            } => {
                let status = if *is_error { "error" } else { "ok" };
                lines.push(Line::from(format!("tool result · {tool_name} · {status}")));
                lines.push(Line::from(truncate_for_prompt(output, 600)));
            }
        }
    }
    lines
}

fn format_tool_panel(summary: &mammoth_runtime::TurnSummary) -> String {
    let tool_uses = collect_tool_uses(summary);
    let tool_results = collect_tool_results(summary);
    if tool_uses.is_empty() && tool_results.is_empty() {
        return "No tool calls in the latest turn.".to_string();
    }

    let mut lines = vec!["Latest turn tool activity".to_string()];
    if !tool_uses.is_empty() {
        lines.push(String::new());
        lines.push("Tool calls".to_string());
        for tool_use in tool_uses {
            lines.push(format!("  {tool_use}"));
        }
    }
    if !tool_results.is_empty() {
        lines.push(String::new());
        lines.push("Tool results".to_string());
        for tool_result in tool_results {
            lines.push(format!("  {tool_result}"));
        }
    }
    lines.join("\n")
}

fn centered_rect(width_percent: u16, height_percent: u16, area: Rect) -> Rect {
    let vertical = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - height_percent) / 2),
            Constraint::Percentage(height_percent),
            Constraint::Percentage((100 - height_percent) / 2),
        ])
        .split(area);
    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - width_percent) / 2),
            Constraint::Percentage(width_percent),
            Constraint::Percentage((100 - width_percent) / 2),
        ])
        .split(vertical[1])[1]
}

fn shrink(area: Rect, padding: u16) -> Rect {
    Rect {
        x: area.x.saturating_add(padding),
        y: area.y.saturating_add(padding),
        width: area.width.saturating_sub(padding * 2),
        height: area.height.saturating_sub(padding * 2),
    }
}

fn previous_boundary(text: &str, index: usize) -> usize {
    if index == 0 {
        return 0;
    }
    text[..index]
        .char_indices()
        .next_back()
        .map_or(0, |(idx, _)| idx)
}

fn next_boundary(text: &str, index: usize) -> usize {
    if index >= text.len() {
        return text.len();
    }
    text[index..]
        .char_indices()
        .nth(1)
        .map_or(text.len(), |(offset, _)| index + offset)
}

fn line_start(text: &str, index: usize) -> usize {
    text[..index].rfind('\n').map_or(0, |pos| pos + 1)
}

fn line_end(text: &str, index: usize) -> usize {
    text[index..]
        .find('\n')
        .map_or(text.len(), |offset| index + offset)
}

fn command_label(command: &SlashCommand) -> String {
    match command {
        SlashCommand::Commit => "/commit".to_string(),
        SlashCommand::Pr { .. } => "/pr".to_string(),
        SlashCommand::Issue { .. } => "/issue".to_string(),
        SlashCommand::Branch { .. } => "/branch".to_string(),
        SlashCommand::Worktree { .. } => "/worktree".to_string(),
        SlashCommand::CommitPushPr { .. } => "/commit-push-pr".to_string(),
        SlashCommand::Resume { .. } => "/resume".to_string(),
        SlashCommand::Init => "/init".to_string(),
        SlashCommand::Export { .. } => "/export".to_string(),
        SlashCommand::Session { .. } => "/session".to_string(),
        SlashCommand::Plugins { .. } => "/plugins".to_string(),
        other => format!("{other:?}"),
    }
}

#[cfg(test)]
mod tests {
    use super::{Composer, PaletteState};

    #[test]
    fn palette_filters_by_name_or_summary() {
        let palette = PaletteState::new("stat".to_string());
        let matches = palette.filtered_specs();
        assert!(matches.iter().any(|spec| spec.name == "status"));
    }

    #[test]
    fn composer_handles_basic_editing() {
        let mut composer = Composer::default();
        composer.insert_char('h');
        composer.insert_char('i');
        composer.move_left();
        composer.insert_char('!');
        composer.delete();
        composer.move_end();
        composer.insert_newline();
        composer.insert_char('o');
        composer.insert_char('k');

        assert_eq!(composer.text, "h!\nok");
    }
}
