"""GraphQL transport adapter for AICP.

Provides GraphQL-based capability execution.
"""

import json
from typing import Any

from aicp.plugins import TransportPlugin, PluginMetadata, register_transport


@register_transport("graphql")
class GraphQLTransport(TransportPlugin):
    """GraphQL transport for capability execution.
    
    Executes capabilities as GraphQL queries/mutations.
    """
    
    def __init__(
        self,
        url: str | None = None,
        endpoint: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.url = url
        self.endpoint = endpoint or "/graphql"
        self.headers = headers or {}
        
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="graphql-transport",
            version="1.0.0",
            description="GraphQL transport for capability execution",
            tags=["graphql", "api", "query"],
        )
        
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self.url = config.get("url", self.url)
            self.endpoint = config.get("endpoint", self.endpoint)
            self.headers = config.get("headers", self.headers)
            
    def shutdown(self) -> None:
        pass
        
    def get_transport_type(self) -> str:
        return "graphql"
    
    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute GraphQL query/mutation.
        
        Request format:
        {
            "query": "mutation { capability(name: $name, args: $args) { result } }",
            "variables": {"name": "tool.name", "args": {...}}
        }
        """
        import aiohttp
        
        full_url = f"{self.url}{self.endpoint}" if self.url else self.endpoint
        
        payload = {
            "query": request.get("query"),
            "variables": request.get("variables", {}),
            "operationName": request.get("operationName"),
        }
        
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(full_url, json=payload, headers=headers) as response:
                result = await response.json()
                
                if "errors" in result:
                    return {
                        "success": False,
                        "errors": result["errors"],
                    }
                return {
                    "success": True,
                    "data": result.get("data"),
                }
    
    async def receive(self) -> dict[str, Any]:
        """Receive response (not used for GraphQL)."""
        raise NotImplementedError("Use send() for GraphQL")


class GraphQLSchemaGenerator:
    """Generate GraphQL schema from AICP capabilities.
    
    Converts registered capabilities into GraphQL schema with queries and mutations.
    """
    
    def __init__(self):
        self._capabilities = {}
        
    def add_capability(self, name: str, description: str, input_fields: dict, output_type: str) -> None:
        """Add a capability to the schema."""
        self._capabilities[name] = {
            "description": description,
            "input": input_fields,
            "output": output_type,
        }
        
    def generate_schema(self) -> str:
        """Generate GraphQL schema string."""
        schema_lines = [
            '"""AICP Capability Schema"""',
            "type Query {",
        ]
        
        queries = []
        mutations = []
        
        for name, cap in self._capabilities.items():
            field_name = name.replace(".", "_")
            args = ", ".join(f"$arg{i}: {graphql_type}" for i, (_, t) in enumerate(cap["input"].items()))
            
            query_field = f"  {field_name}({args}): {cap['output']}"
            mutation_field = f"  execute{field_name.replace('_', '').title()}({args}): {cap['output']}"
            
            queries.append(query_field)
            mutations.append(mutation_field)
            
        schema_lines.extend(queries + ["}", "", "type Mutation {"] + mutations + ["}", ""])
        schema_lines.extend(self._generate_types())
        
        return "\n".join(schema_lines)
    
    def _generate_types(self) -> list[str]:
        """Generate output types."""
        types = []
        for cap in self._capabilities.values():
            if cap["output"] != "String" and cap["output"] != "Boolean":
                types.append(f"type {cap['output']} {{")
                types.append("  # Add fields based on output schema")
                types.append("}")
        return types


def graphql_query_from_capability(capability_name: str, arguments: dict[str, Any]) -> str:
    """Generate GraphQL query string from capability and arguments.
    
    Args:
        capability_name: Name of capability to call.
        arguments: Arguments for the capability.
        
    Returns:
        GraphQL query string.
    """
    field_name = capability_name.replace(".", "_")
    
    vars_list = []
    for i, (key, value) in enumerate(arguments.items()):
        vars_list.append(f"$arg{i}: String")
        
    args_list = []
    for i, key in enumerate(arguments.keys()):
        args_list.append(f"{key}: $arg{i}")
    
    query = f"""
query {field_name}({', '.join(vars_list)}) {{
  {field_name}({', '.join(args_list)}) {{
    success
    data
  }}
}}
"""
    return query.strip()
