use mammoth_runtime::permissions::AuditLog;

pub struct AuditPermissionsArgs {
    pub last: usize,
}

pub fn run(log: &AuditLog, args: AuditPermissionsArgs) {
    for entry in log.last_n(args.last) {
        println!("{entry:?}");
    }
}

#[cfg(test)]
mod tests {
    use super::{run, AuditPermissionsArgs};
    use mammoth_runtime::permissions::{AuditLog, PermissionAuditEntry};
    use std::time::{SystemTime, UNIX_EPOCH};

    fn now_ms() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64
    }

    fn make_log() -> AuditLog {
        let mut log = AuditLog::new(50);
        log.record(PermissionAuditEntry {
            timestamp_ms: now_ms(),
            tool_name: "bash".to_string(),
            input_preview: "echo hi".to_string(),
            outcome: "allow".to_string(),
            mode_at_time: "allow".to_string(),
        });
        log.record(PermissionAuditEntry {
            timestamp_ms: now_ms(),
            tool_name: "write_file".to_string(),
            input_preview: "/etc/passwd".to_string(),
            outcome: "deny: denied by policy".to_string(),
            mode_at_time: "read-only".to_string(),
        });
        log
    }

    #[test]
    fn run_does_not_panic_with_zero() {
        let log = make_log();
        run(&log, AuditPermissionsArgs { last: 0 });
    }

    #[test]
    fn run_does_not_panic_with_entries() {
        let log = make_log();
        run(&log, AuditPermissionsArgs { last: 5 });
    }
}
