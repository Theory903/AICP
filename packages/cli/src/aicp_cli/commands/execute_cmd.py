"""Execute capability command."""

import json
import click
from aicp_cli.context import get_runtime_context


@click.command("run")
@click.argument("capability")
@click.option("--input", "-i", "input_data", help="JSON input string or @file path")
@click.option("--context", "-c", "context_data", default="{}", help="JSON context")
@click.pass_context
def run_cmd(ctx, capability, input_data, context_data):
    """Execute a capability by name.
    
    Examples:
        aicp run notes.create -i '{"title": "Hello"}'
        aicp run notes.list
        aicp run notes.delete -i @fixture.json
    """
    import asyncio

    # 1. Prepare input arguments
    args = {}
    if input_data:
        try:
            if input_data.startswith("@"):
                with open(input_data[1:]) as f:
                    args = json.load(f)
            else:
                args = json.loads(input_data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            click.secho(f"Error: Failed to load input data: {e}", fg="red")
            return

    # 2. Prepare context
    try:
        context = json.loads(context_data)
    except json.JSONDecodeError as e:
        click.secho(f"Error: Failed to parse context data: {e}", fg="red")
        return

    return asyncio.run(_run_execution(capability, args, context))


async def _run_execution(capability_name, args, context):
    runtime = get_runtime_context()
    
    cap = await runtime.project.repository.get_capability(capability_name)
    if not cap:
        click.secho(f"Error: Capability '{capability_name}' not found.", fg="red", bold=True)
        return

    # 3. Add capability kind to context for policy check consistency
    context["kind"] = cap.kind.value
    context["is_destructive"] = getattr(cap, "is_destructive", False)

    try:
        result = await runtime.project.executor.execute(capability_name, args, context)
        
        # 4. Result normalization and pretty printing
        output = result
        if hasattr(result, "model_dump"):
            output = result.model_dump(exclude_none=True, mode="json")
            
        click.echo(json.dumps(output, indent=2))
        
    except Exception as e:
        # Avoid bare except. Show the error clearly.
        click.secho(f"Execution failed: {e}", fg="red", bold=True)
        if hasattr(e, "__traceback__"):
            # Optionally show more debug info if verbose mode was set
            pass
