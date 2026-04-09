import socket
from dataclasses import dataclass, field
from ipaddress import AddressValueError, IPv4Address, IPv6Address


class SSRFBlockedError(Exception):
    pass


BLOCKED_HOSTNAMES: frozenset[str] = frozenset([
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
])


BLOCKED_IPV4_RANGES = [
    (IPv4Address("127.0.0.0"), IPv4Address("127.255.255.255")),
    (IPv4Address("10.0.0.0"), IPv4Address("10.255.255.255")),
    (IPv4Address("172.16.0.0"), IPv4Address("172.31.255.255")),
    (IPv4Address("192.168.0.0"), IPv4Address("192.168.255.255")),
    (IPv4Address("169.254.0.0"), IPv4Address("169.254.255.255")),
    (IPv4Address("0.0.0.0"), IPv4Address("0.255.255.255")),
    (IPv4Address("255.255.255.255"), IPv4Address("255.255.255.255")),
    (IPv4Address("224.0.0.0"), IPv4Address("239.255.255.255")),
    (IPv4Address("100.64.0.0"), IPv4Address("100.127.255.255")),
    (IPv4Address("240.0.0.0"), IPv4Address("255.255.255.255")),
    (IPv4Address("198.18.0.0"), IPv4Address("198.19.255.255")),
]


BLOCKED_IPV6_RANGES = [
    (IPv6Address("::"), IPv6Address("::ffff:ffff:ffff:ffff")),
    (IPv6Address("::1"), IPv6Address("::1")),
    (IPv6Address("fe80::"), IPv6Address("febf:ffff:ffff:ffff:ffff:ffff:ffff:ffff")),
    (IPv6Address("fc00::"), IPv6Address("fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff")),
    (IPv6Address("ff00::"), IPv6Address("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff")),
    (IPv6Address("::ffff:0.0.0.0"), IPv6Address("::ffff:255.255.255.255")),
]


RFC2544_RANGE = (
    IPv4Address("198.18.0.0"),
    IPv4Address("198.19.255.255"),
)


@dataclass(frozen=True)
class SSRFPolicy:
    allow_private_network: bool = False
    dangerously_allow_private_network: bool = False
    allow_rfc2544_benchmark_range: bool = False
    blocked_hostnames: frozenset[str] = field(default_factory=lambda: frozenset([
        "localhost",
        "metadata.google.internal",
    ]))
    hostname_allowlist: frozenset[str] = field(default_factory=frozenset)
    dns_rebinding_protection: bool = True
    max_dns_cache_seconds: int = 300

    @classmethod
    def from_dict(cls, data: dict | None) -> "SSRFPolicy":
        if data is None:
            return cls()
        return cls(
            allow_private_network=data.get("allow_private_network", False),
            dangerously_allow_private_network=data.get("dangerously_allow_private_network", False),
            allow_rfc2544_benchmark_range=data.get("allow_rfc2544_benchmark_range", False),
            blocked_hostnames=frozenset(data.get("blocked_hostnames", [
                "localhost",
                "metadata.google.internal",
            ])),
            hostname_allowlist=frozenset(data.get("hostname_allowlist", [])),
            dns_rebinding_protection=data.get("dns_rebinding_protection", True),
            max_dns_cache_seconds=data.get("max_dns_cache_seconds", 300),
        )


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = IPv4Address(ip_str)
        return any(start <= ip <= end for start, end in BLOCKED_IPV4_RANGES)
    except AddressValueError:
        try:
            ip = IPv6Address(ip_str)
            return any(start <= ip <= end for start, end in BLOCKED_IPV6_RANGES)
        except AddressValueError:
            return False


def _normalize_hostname(hostname: str) -> str:
    return hostname.strip().lower()


def _is_hostname_blocked(hostname: str) -> bool:
    normalized = _normalize_hostname(hostname)
    if not normalized:
        return False
    if normalized in BLOCKED_HOSTNAMES:
        return True
    return normalized.endswith(".localhost") or normalized.endswith(".local") or normalized.endswith(".internal")


def _matches_hostname_pattern(hostname: str, pattern: str) -> bool:
    normalized_hostname = _normalize_hostname(hostname)
    if pattern.startswith("*."):
        suffix = pattern[2:]
        if not suffix or normalized_hostname == suffix:
            return False
        return normalized_hostname.endswith(f".{suffix}")
    return normalized_hostname == _normalize_hostname(pattern)


def _check_ip_in_range(ip_str: str, start: IPv4Address, end: IPv4Address) -> bool:
    try:
        ip = IPv4Address(ip_str)
        return start <= ip <= end
    except AddressValueError:
        return False


def is_private_ip_address(ip_str: str, policy: SSRFPolicy | None = None) -> bool:
    normalized = ip_str.strip().lower()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    if not normalized:
        return False
    if policy and policy.allow_rfc2544_benchmark_range and _check_ip_in_range(
        normalized, RFC2544_RANGE[0], RFC2544_RANGE[1]
    ):
        return False
    return _is_private_ip(normalized)


def is_blocked_hostname(hostname: str, policy: SSRFPolicy | None = None) -> bool:
    normalized = _normalize_hostname(hostname)
    if not normalized:
        return False
    if _is_hostname_blocked(normalized):
        return True
    if policy and policy.blocked_hostnames:
        if normalized in policy.blocked_hostnames:
            return True
        for blocked in policy.blocked_hostnames:
            if blocked.startswith("*."):
                suffix = blocked[2:]
                if normalized.endswith(f".{suffix}") or normalized == suffix:
                    return True
    return False


def is_blocked_hostname_or_ip(hostname_or_ip: str, policy: SSRFPolicy | None = None) -> bool:
    normalized = _normalize_hostname(hostname_or_ip)
    if not normalized:
        return False
    if is_blocked_hostname(normalized, policy):
        return True
    return bool(is_private_ip_address(normalized, policy))


def _resolve_hostname(hostname: str) -> list[str]:
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return list(dict.fromkeys(str(r[4][0]) for r in results))
    except socket.gaierror:
        return []


def _is_hostname_allowed_by_allowlist(hostname: str, policy: SSRFPolicy | None) -> bool:
    if not policy or not policy.hostname_allowlist:
        return False
    return any(_matches_hostname_pattern(hostname, pattern) for pattern in policy.hostname_allowlist)


def _is_private_network_allowed_by_policy(policy: SSRFPolicy | None) -> bool:
    if not policy:
        return False
    return policy.allow_private_network or policy.dangerously_allow_private_network


def assert_allowed_host_or_ip(hostname_or_ip: str, policy: SSRFPolicy | None = None) -> None:
    if is_blocked_hostname_or_ip(hostname_or_ip, policy):
        raise SSRFBlockedError(
            f"Blocked hostname or private/internal/special-use IP address: {hostname_or_ip}"
        )


def assert_allowed_resolved_addresses(
    addresses: list[str],
    policy: SSRFPolicy | None = None
) -> None:
    for addr in addresses:
        if is_private_ip_address(addr, policy):
            raise SSRFBlockedError(
                f"Blocked: resolves to private/internal/special-use IP address: {addr}"
            )


def validate_url(
    url: str,
    policy: SSRFPolicy | None = None,
    resolve_dns: bool = True
) -> None:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise ValueError(f"Invalid URL: no hostname found in {url}")

    if is_blocked_hostname(hostname, policy):
        raise SSRFBlockedError(f"Blocked hostname: {hostname}")

    allowlist_bypass = _is_hostname_allowed_by_allowlist(hostname, policy)
    private_network_allowed = _is_private_network_allowed_by_policy(policy)
    skip_private_checks = allowlist_bypass or private_network_allowed

    if not skip_private_checks:
        assert_allowed_host_or_ip(hostname, policy)

    if resolve_dns and policy and policy.dns_rebinding_protection and not skip_private_checks:
        resolved_ips = _resolve_hostname(hostname)
        if resolved_ips:
            assert_allowed_resolved_addresses(resolved_ips, policy)
        else:
            raise SSRFBlockedError(f"Unable to resolve hostname: {hostname}")


def validate_and_resolve_hostname(
    hostname: str,
    policy: SSRFPolicy | None = None
) -> list[str]:
    if not hostname:
        raise ValueError("Hostname is required")

    normalized = _normalize_hostname(hostname)

    if policy and policy.hostname_allowlist and not _is_hostname_allowed_by_allowlist(normalized, policy):
        raise SSRFBlockedError(f"Blocked hostname (not in allowlist): {hostname}")

    skip_private_checks = (
        _is_hostname_allowed_by_allowlist(normalized, policy) or
        _is_private_network_allowed_by_policy(policy)
    )

    if not skip_private_checks:
        assert_allowed_host_or_ip(normalized, policy)

    resolved_ips = _resolve_hostname(normalized)
    if not resolved_ips:
        raise ValueError(f"Unable to resolve hostname: {hostname}")

    if not skip_private_checks:
        assert_allowed_resolved_addresses(resolved_ips, policy)

    return resolved_ips


def check_ssrf_safe(url: str, policy: SSRFPolicy | None = None) -> bool:
    try:
        validate_url(url, policy)
        return True
    except (SSRFBlockedError, ValueError):
        return False
