use anyhow::Result;
use std::fmt::Write;

use crate::session::{ContentBlock, MessageRole, Session};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExportFormat {
    Json,
    Markdown,
}

impl ExportFormat {
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_ascii_lowercase().as_str() {
            "json" => Some(Self::Json),
            "md" | "markdown" => Some(Self::Markdown),
            _ => None,
        }
    }
}

pub struct SessionExporter<'a> {
    session: &'a Session,
}

impl<'a> SessionExporter<'a> {
    #[must_use]
    pub fn new(session: &'a Session) -> Self {
        Self { session }
    }

    pub fn to_json(&self) -> Result<String> {
        Ok(serde_json::to_string_pretty(self.session)?)
    }

    #[must_use]
    pub fn to_markdown(&self) -> String {
        let mut md = String::from("# Mammoth Session Export\n\n");
        for msg in &self.session.messages {
            let heading = match msg.role {
                MessageRole::User => "## User",
                MessageRole::Assistant => "## Assistant",
                _ => "## Other",
            };
            md.push_str(heading);
            md.push('\n');
            for block in &msg.blocks {
                match block {
                    ContentBlock::Text { text } => {
                        md.push_str(text);
                        md.push('\n');
                    }
                    ContentBlock::ToolUse { name, input, .. } => {
                        write!(md, "**Tool:** `{name}`\n```json\n{input}\n```\n").unwrap();
                    }
                    ContentBlock::ToolResult { output, .. } => {
                        write!(md, "**Result:** {output}\n").unwrap();
                    }
                }
            }
            md.push('\n');
        }
        md
    }

    pub fn export(&self, format: ExportFormat) -> Result<String> {
        match format {
            ExportFormat::Json => self.to_json(),
            ExportFormat::Markdown => Ok(self.to_markdown()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session::Session;

    fn session_with_messages() -> Session {
        let mut s = Session::new();
        s.messages
            .push(crate::session::ConversationMessage::user_text(
                "Deploy to prod?",
            ));
        s.messages
            .push(crate::session::ConversationMessage::assistant_text(
                "Deploying now.",
            ));
        s
    }

    #[test]
    fn export_json_is_valid_json() {
        let session = session_with_messages();
        let exporter = SessionExporter::new(&session);
        let json = exporter.to_json().expect("json export");
        let parsed: serde_json::Value = serde_json::from_str(&json).expect("parse");
        assert!(parsed.get("messages").is_some());
    }

    #[test]
    fn export_markdown_contains_headings_and_content() {
        let session = session_with_messages();
        let exporter = SessionExporter::new(&session);
        let md = exporter.to_markdown();
        assert!(md.contains("## User"));
        assert!(md.contains("## Assistant"));
        assert!(md.contains("Deploy to prod?"));
        assert!(md.contains("Deploying now."));
    }

    #[test]
    fn export_format_from_str() {
        assert_eq!(ExportFormat::parse("json"), Some(ExportFormat::Json));
        assert_eq!(ExportFormat::parse("md"), Some(ExportFormat::Markdown));
        assert_eq!(
            ExportFormat::parse("markdown"),
            Some(ExportFormat::Markdown)
        );
        assert_eq!(ExportFormat::parse("pdf"), None);
    }
}
