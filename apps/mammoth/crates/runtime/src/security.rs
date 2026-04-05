use std::net::IpAddr;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SsrfCheckResult {
    Allowed,
    Blocked { reason: String },
}

#[derive(Debug, Clone, Default)]
pub struct SsrfGuard;

impl SsrfGuard {
    #[must_use]
    pub fn check_url(&self, url: &str) -> SsrfCheckResult {
        let parsed = match url::Url::parse(url) {
            Ok(u) => u,
            Err(_) => {
                return SsrfCheckResult::Blocked {
                    reason: "unparseable url".to_string(),
                }
            }
        };
        let host = match parsed.host() {
            Some(url::Host::Ipv4(ip)) => IpAddr::V4(ip),
            Some(url::Host::Ipv6(ip)) => IpAddr::V6(ip),
            Some(url::Host::Domain(_)) => return SsrfCheckResult::Allowed,
            None => {
                return SsrfCheckResult::Blocked {
                    reason: "no host in url".to_string(),
                }
            }
        };
        if is_blocked_ip(&host) {
            SsrfCheckResult::Blocked {
                reason: format!("address {host} is not routable"),
            }
        } else {
            SsrfCheckResult::Allowed
        }
    }
}

fn is_blocked_ip(addr: &IpAddr) -> bool {
    match addr {
        IpAddr::V4(ip) => {
            let octets = ip.octets();
            ip.is_loopback()
                || ip.is_link_local()
                || octets[0] == 10
                || (octets[0] == 172 && (16..=31).contains(&octets[1]))
                || (octets[0] == 192 && octets[1] == 168)
        }
        IpAddr::V6(ip) => ip.is_loopback() || (ip.segments()[0] & 0xfe00) == 0xfc00,
    }
}
