use ratatui::prelude::*;

pub struct TaskProgress {
    task_id: String,
    description: String,
    percent: u8,
    status: TaskStatus,
}

#[derive(Debug, Clone, PartialEq)]
pub enum TaskStatus {
    Pending,
    Running,
    Completed,
    Failed,
}

impl TaskProgress {
    pub fn new(task_id: String, description: String) -> Self {
        Self {
            task_id,
            description,
            percent: 0,
            status: TaskStatus::Pending,
        }
    }

    pub fn update(&mut self, percent: u8, status: TaskStatus) {
        self.percent = percent;
        self.status = status;
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        let title = format!("{}: {}", self.task_id, self.description);
        buf.set_string(area.x, area.y, title, Style::default());

        let progress_bar = "=".repeat(self.percent as usize / 10);
        let progress_str = format!("[{}{}]", progress_bar, " ".repeat(10 - progress_bar.len()));
        buf.set_string(
            area.x,
            area.y + 1,
            progress_str,
            Style::default().fg(Color::Green),
        );

        let status_str = format!("{:?}", self.status);
        buf.set_string(
            area.x + 15,
            area.y + 1,
            status_str,
            Style::default().fg(Color::White),
        );
    }
}

pub struct TaskList {
    tasks: Vec<TaskProgress>,
    selected: usize,
}

impl TaskList {
    pub fn new() -> Self {
        Self {
            tasks: Vec::new(),
            selected: 0,
        }
    }

    pub fn add_task(&mut self, task: TaskProgress) {
        self.tasks.push(task);
    }

    pub fn render(&self, area: Rect, buf: &mut Buffer) {
        for (i, task) in self.tasks.iter().enumerate() {
            let task_area = Rect::new(area.x, area.y + i as u16, area.width, 3);
            task.render(task_area, buf);
        }
    }
}

impl Default for TaskList {
    fn default() -> Self {
        Self::new()
    }
}
