"""Test commands for AICP runtime testing."""

from __future__ import annotations

import json

import click
import requests


@click.command("test")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
def test_cmd(url: str) -> None:
    """Test AICP runtime endpoints.
    
    Examples:
        aicp test
        aicp test -u http://localhost:9000
    """
    click.echo(f"Testing AICP runtime at {url}")
    click.echo("=" * 50)
    
    results = []
    
    # Test 1: Discovery
    results.append(_test_endpoint("Discovery", "GET", f"{url}/.well-known/aicp"))
    
    # Test 2: Health
    results.append(_test_endpoint("App Health", "GET", f"{url}/health", expect_status=200))
    
    # Test 3: V1 capabilities rank
    results.append(_test_endpoint("Rank", "GET", f"{url}/v1/capabilities/rank?query=grades"))
    
    # Test 4: Sessions
    results.append(_test_endpoint("Sessions", "GET", f"{url}/v1/sessions"))
    
    # Test 5: Interactions
    results.append(_test_endpoint("Interactions", "GET", f"{url}/v1/interactions"))
    
    # Test 6: Executions
    results.append(_test_endpoint("Executions", "GET", f"{url}/v1/executions"))
    
    # Test 7: Provider Health
    results.append(_test_endpoint("Provider Health", "GET", f"{url}/providers/health"))
    
    # Test 8: Approvals
    results.append(_test_endpoint("Approvals", "GET", f"{url}/approvals"))
    
    # Test 9: Console
    results.append(_test_endpoint("Console", "GET", f"{url}/console", expect_status=200))
    
    # Test 10: Execute query
    results.append(_test_endpoint("Execute query", "POST", f"{url}/v1/execute", data={
        "capability_name": "grades.list",
        "arguments": {}
    }))
    
    # Summary
    click.echo("\n" + "=" * 50)
    passed = sum(1 for r in results if r["status"] == "✓")
    total = len(results)
    click.echo(f"Results: {passed}/{total} passed")
    
    if passed == total:
        click.secho("All tests passed!", fg="green")
    else:
        click.secho("Some tests failed!", fg="red")
        for r in results:
            if r["status"] != "✓":
                click.echo(f"  - {r['name']}: {r.get('error', 'failed')}")


def _test_endpoint(
    name: str,
    method: str,
    url: str,
    data: dict | None = None,
    expect_status: int = 200,
) -> dict:
    """Test a single endpoint."""
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=data or {}, timeout=10)
        
        if r.status_code == expect_status or (expect_status == 200 and r.status_code < 400):
            click.echo(f"✓ {name}: {r.status_code}")
            return {"name": name, "status": "✓", "code": r.status_code}
        else:
            click.echo(f"✗ {name}: {r.status_code} (expected {expect_status})")
            return {"name": name, "status": "✗", "error": f"status {r.status_code}"}
    except Exception as e:
        click.echo(f"✗ {name}: {e}")
        return {"name": name, "status": "✗", "error": str(e)}


@click.command("test:execute")
@click.argument("capability")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
@click.option("--input", "-i", "input_data", default="{}", help="JSON arguments")
def test_execute_cmd(url: str, capability: str, input_data: str) -> None:
    """Execute a capability against the running server.
    
    Examples:
        aicp test:execute grades.list
        aicp test:execute grades.create -i '{"name": "Test", "numeric_value": 90}'
    """
    try:
        args = json.loads(input_data)
    except json.JSONDecodeError as e:
        click.secho(f"Invalid JSON: {e}", fg="red")
        return
    
    click.echo(f"Executing: {capability}")
    click.echo(f"Arguments: {args}")
    click.echo("-" * 40)
    
    try:
        r = requests.post(
            f"{url}/v1/execute",
            json={"capability_name": capability, "arguments": args},
            timeout=30
        )
        
        result = r.json()
        
        click.echo(f"Status: {result.get('status')}")
        
        if result.get('data'):
            click.echo(f"Data: {json.dumps(result['data'], indent=2)}")
        
        if result.get('error'):
            click.secho(f"Error: {json.dumps(result['error'], indent=2)}", fg="red")
        
        if result.get('approval_status'):
            click.echo(f"Approval: {result.get('approval_status')}")
        
        if result.get('approval_request_id'):
            click.echo(f"Approval ID: {result.get('approval_request_id')}")
            
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")


@click.command("test:approvals")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
def test_approvals_cmd(url: str) -> None:
    """List and manage approvals.
    
    Examples:
        aicp test:approvals
    """
    r = requests.get(f"{url}/approvals", timeout=10)
    approvals = r.json()
    
    if not approvals:
        click.echo("No pending approvals")
        return
    
    click.echo(f"Found {len(approvals)} approvals:\n")
    
    for a in approvals:
        click.echo(f"  ID: {a.get('id')}")
        click.echo(f"  Capability: {a.get('capability_name')}")
        click.echo(f"  Arguments: {a.get('arguments')}")
        click.echo(f"  Status: {a.get('status')}")
        click.echo(f"  Requested: {a.get('requested_at')}")
        click.echo("-" * 20)


@click.command("test:approve")
@click.argument("approval_id")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
@click.option("--decision", "-d", default="approved", help="Decision (approved/rejected)")
@click.option("--approver", "-a", default="cli", help="Approver name")
def test_approve_cmd(url: str, approval_id: str, decision: str, approver: str) -> None:
    """Approve or reject an approval request.
    
    Examples:
        aicp test:approve apr_123456
        aicp test:approve apr_123456 -d rejected -a admin
    """
    r = requests.post(
        f"{url}/approvals/{approval_id}/decide",
        json={"decision": decision, "approver": approver},
        timeout=10
    )
    
    result = r.json()
    
    click.echo(f"Decision: {decision}")
    click.echo(f"Status: {r.status_code}")
    click.echo(json.dumps(result, indent=2))


@click.command("test:review")
@click.argument("approval_id")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
def test_review_cmd(url: str, approval_id: str) -> None:
    """Get approval review packet with impact analysis.
    
    Examples:
        aicp test:review apr_123456
    """
    r = requests.get(f"{url}/approvals/{approval_id}/review-packet", timeout=10)
    packet = r.json()
    
    impact = packet.get('impact_summary', {})
    
    click.echo(f"Approval: {approval_id}")
    click.echo("-" * 40)
    click.echo(f"Risk Level: {impact.get('risk_level')}")
    click.echo(f"Destructive: {impact.get('destructive')}")
    click.echo(f"Blast Radius: {impact.get('blast_radius_estimate')}")
    click.echo(f"Data Classification: {impact.get('data_classification')}")
    click.echo(f"Compliance Flags: {impact.get('compliance_flags')}")
    click.echo(f"Time Sensitivity: {impact.get('time_sensitivity')}")
    click.echo(f"Reversible: {impact.get('reversible')}")
    click.echo(f"Rollback Capability: {impact.get('rollback_capability')}")


@click.command("test:rank")
@click.argument("query", required=False, default="")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
@click.option("--limit", "-n", default=5, help="Number of results")
def test_rank_cmd(url: str, query: str, limit: int) -> None:
    """Rank capabilities by query.
    
    Examples:
        aicp test:rank grades
        aicp test:rank "grade create"
    """
    r = requests.get(
        f"{url}/v1/capabilities/rank",
        params={"query": query, "limit": limit},
        timeout=10
    )
    results = r.json()
    
    click.echo(f"Query: '{query}'")
    click.echo(f"Found {len(results)} results:\n")
    
    for i, item in enumerate(results):
        cap = item['capability']
        click.echo(f"{i+1}. {cap['name']}")
        click.echo(f"   Score: {item['score']}")
        click.echo(f"   Kind: {cap['kind']}")
        click.echo(f"   Description: {cap['description']}")
        if item.get('reasons'):
            click.echo(f"   Reasons: {', '.join(item['reasons'])}")
        click.echo()


@click.command("test:health")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
def test_health_cmd(url: str) -> None:
    """Show provider health metrics.
    
    Examples:
        aicp test:health
    """
    r = requests.get(f"{url}/providers/health", timeout=10)
    health = r.json()
    
    click.echo("Provider Health:")
    click.echo("=" * 40)
    
    for p in health:
        click.echo(f"\n{p['provider_name']} ({p['provider_type']}):")
        click.echo(f"  Status: {p['health_status']}")
        click.echo(f"  Success Rate: {p.get('success_rate', 0):.1%}")
        click.echo(f"  Failure Rate: {p.get('failure_rate', 0):.1%}")
        click.echo(f"  Auth Failure Rate: {p.get('auth_failure_rate', 0):.1%}")
        click.echo(f"  Network Failure Rate: {p.get('network_failure_rate', 0):.1%}")
        click.echo(f"  Recent Latency: {p.get('recent_latency_ms')}ms")
        click.echo(f"  Last Error: {p.get('last_error_code')}")


@click.command("test:sessions")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
def test_sessions_cmd(url: str) -> None:
    """List and manage sessions.
    
    Examples:
        aicp test:sessions
    """
    r = requests.get(f"{url}/v1/sessions", timeout=10)
    sessions = r.json()
    
    click.echo(f"Sessions: {len(sessions)}")
    
    for s in sessions:
        click.echo(f"\n  ID: {s.get('id')}")
        click.echo(f"  Provider: {s.get('provider_name')}")
        click.echo(f"  Status: {s.get('status')}")
        click.echo(f"  Created: {s.get('created_at')}")


@click.command("test:interactions")
@click.option("--url", "-u", default="http://127.0.0.1:8000", help="Runtime URL")
def test_interactions_cmd(url: str) -> None:
    """List interactions.
    
    Examples:
        aicp test:interactions
    """
    r = requests.get(f"{url}/v1/interactions", timeout=10)
    interactions = r.json()
    
    click.echo(f"Interactions: {len(interactions)}")
    
    for i in interactions:
        click.echo(f"\n  ID: {i.get('id')}")
        click.echo(f"  Last Capability: {i.get('last_capability')}")
        click.echo(f"  Last Status: {i.get('last_status')}")
        click.echo(f"  Updated: {i.get('updated_at')}")
