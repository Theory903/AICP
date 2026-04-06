import pytest
from aicp.security.ssrf import (
    SSRFBlockedError,
    SSRFPolicy,
    is_private_ip_address,
    is_blocked_hostname,
    is_blocked_hostname_or_ip,
    validate_url,
    validate_and_resolve_hostname,
    check_ssrf_safe,
)


class TestIsPrivateIpAddress:
    def test_blocks_loopback(self):
        assert is_private_ip_address("127.0.0.1") is True
        assert is_private_ip_address("127.255.255.255") is True

    def test_blocks_private_networks(self):
        assert is_private_ip_address("10.0.0.1") is True
        assert is_private_ip_address("172.16.0.1") is True
        assert is_private_ip_address("192.168.1.1") is True

    def test_blocks_link_local(self):
        assert is_private_ip_address("169.254.0.1") is True

    def test_blocks_multicast(self):
        assert is_private_ip_address("224.0.0.1") is True
        assert is_private_ip_address("239.255.255.255") is True

    def test_allows_public_ip(self):
        assert is_private_ip_address("8.8.8.8") is False
        assert is_private_ip_address("1.1.1.1") is False
        assert is_private_ip_address("93.184.216.34") is False

    def test_handles_brackets(self):
        assert is_private_ip_address("[127.0.0.1]") is True

    def test_allows_rfc2544_with_policy(self):
        policy = SSRFPolicy(allow_rfc2544_benchmark_range=True)
        assert is_private_ip_address("198.18.0.1", policy) is False

    def test_blocks_rfc2544_without_policy(self):
        assert is_private_ip_address("198.18.0.1") is True


class TestIsBlockedHostname:
    def test_blocks_localhost(self):
        assert is_blocked_hostname("localhost") is True
        assert is_blocked_hostname("LOCALHOST") is True

    def test_blocks_metadata_google(self):
        assert is_blocked_hostname("metadata.google.internal") is True

    def test_blocks_local_suffix(self):
        assert is_blocked_hostname("anything.local") is True
        assert is_blocked_hostname("anything.localhost") is True
        assert is_blocked_hostname("anything.internal") is True

    def test_allows_public_hostname(self):
        assert is_blocked_hostname("example.com") is False
        assert is_blocked_hostname("api.github.com") is False

    def test_respects_policy_blocked(self):
        policy = SSRFPolicy(blocked_hostnames=frozenset(["evil.com", "*.evil.com"]))
        assert is_blocked_hostname("evil.com", policy) is True
        assert is_blocked_hostname("sub.evil.com", policy) is True


class TestIsBlockedHostnameOrIp:
    def test_blocks_private_ip(self):
        assert is_blocked_hostname_or_ip("192.168.1.1") is True

    def test_blocks_blocked_hostname(self):
        assert is_blocked_hostname_or_ip("localhost") is True

    def test_allows_public_combination(self):
        assert is_blocked_hostname_or_ip("8.8.8.8") is False
        assert is_blocked_hostname_or_ip("example.com") is False


class TestValidateUrl:
    def test_allows_public_url(self):
        validate_url("https://example.com/path")
        validate_url("http://api.github.com/users")

    def test_blocks_private_ip_url(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("http://192.168.1.1/", resolve_dns=False)
        with pytest.raises(SSRFBlockedError):
            validate_url("http://10.0.0.1/", resolve_dns=False)

    def test_blocks_localhost_url(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("http://localhost/", resolve_dns=False)

    def test_blocks_localhost_with_port(self):
        with pytest.raises(SSRFBlockedError):
            validate_url("http://localhost:8080/api", resolve_dns=False)

    def test_resolves_and_validates_dns(self):
        validate_url("https://example.com", resolve_dns=True)

    def test_allows_with_allowlist(self):
        policy = SSRFPolicy(hostname_allowlist=frozenset(["internal.corp"]))
        validate_url("http://internal.corp/api", policy=policy, resolve_dns=False)

    def test_allows_private_with_policy(self):
        policy = SSRFPolicy(allow_private_network=True)
        validate_url("http://192.168.1.1/api", policy=policy, resolve_dns=False)


class TestValidateAndResolveHostname:
    def test_resolves_public_hostname(self):
        ips = validate_and_resolve_hostname("example.com")
        assert len(ips) > 0
        assert all(
            ("." in ip and ip.count(".") == 3) or ":" in ip for ip in ips
        )

    def test_raises_for_blocked_hostname(self):
        with pytest.raises(SSRFBlockedError):
            validate_and_resolve_hostname("localhost")

    def test_raises_for_empty_hostname(self):
        with pytest.raises(ValueError):
            validate_and_resolve_hostname("")


class TestCheckSsrfSafe:
    def test_returns_true_for_safe_url(self):
        assert check_ssrf_safe("https://example.com") is True
        assert check_ssrf_safe("https://api.github.com") is True

    def test_returns_false_for_blocked_url(self):
        assert check_ssrf_safe("http://localhost/") is False
        assert check_ssrf_safe("http://192.168.1.1/") is False
        assert check_ssrf_safe("http://10.0.0.1/") is False

    def test_returns_false_for_invalid_url(self):
        assert check_ssrf_safe("not-a-url") is False

    def test_respects_policy(self):
        policy = SSRFPolicy(allow_private_network=True)
        assert check_ssrf_safe("http://192.168.1.1/", policy=policy) is True


class TestSSRFPolicy:
    def test_from_dict_with_defaults(self):
        policy = SSRFPolicy.from_dict(None)
        assert policy.allow_private_network is False
        assert policy.dns_rebinding_protection is True

    def test_from_dict_with_custom_values(self):
        data = {
            "allow_private_network": True,
            "allow_rfc2544_benchmark_range": True,
            "hostname_allowlist": ["internal.corp", "*.private.com"],
        }
        policy = SSRFPolicy.from_dict(data)
        assert policy.allow_private_network is True
        assert policy.allow_rfc2544_benchmark_range is True
        assert "internal.corp" in policy.hostname_allowlist
        assert "*.private.com" in policy.hostname_allowlist

    def test_default_blocked_hostnames(self):
        policy = SSRFPolicy()
        assert "localhost" in policy.blocked_hostnames
        assert "metadata.google.internal" in policy.blocked_hostnames
