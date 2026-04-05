use mammoth_runtime::security::{SsrfCheckResult, SsrfGuard};

#[test]
fn public_url_is_allowed() {
    let guard = SsrfGuard;
    assert_eq!(
        guard.check_url("https://example.com/api"),
        SsrfCheckResult::Allowed
    );
}

#[test]
fn loopback_ipv4_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://127.0.0.1:8080/secret");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn rfc1918_10_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://10.0.0.1/internal");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn rfc1918_172_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://172.16.0.1/internal");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn rfc1918_192_168_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://192.168.1.100/internal");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn link_local_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://169.254.1.1/metadata");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn ipv6_loopback_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://[::1]/secret");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn ipv6_ula_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("http://[fc00::1]/internal");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}

#[test]
fn domain_name_allowed() {
    let guard = SsrfGuard;
    assert_eq!(
        guard.check_url("https://api.github.com/repos"),
        SsrfCheckResult::Allowed
    );
}

#[test]
fn unparseable_url_blocked() {
    let guard = SsrfGuard;
    let result = guard.check_url("not a url !!!");
    assert!(matches!(result, SsrfCheckResult::Blocked { .. }));
}
