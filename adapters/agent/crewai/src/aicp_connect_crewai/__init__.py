from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CrewAIConfig(BaseModel):
    aicp_base_url: str = "http://localhost:8000"
    session_id: Optional[str] = None


class AicpCrewAITool:
    def __init__(self, name: str, description: str, func: Any):
        self.name = name
        self.description = description
        self.func = func


class AicpCrewAIAdapter:
    def __init__(self, config: Optional[CrewAIConfig] = None):
        self.config = config or CrewAIConfig()
        self._tools: List[AicpCrewAITool] = []

    def add_capability(self, name: str, description: str) -> None:
        import requests
        from aicp_connect_crewai import config

        def func(input: str) -> str:
            url = f"{config.aicp_base_url}/v1/execute"
            payload = {"capability": name, "arguments": {"input": input}}
            if config.session_id:
                payload["session_id"] = config.session_id
            response = requests.post(url, json=payload)
            return response.json()

        tool = AicpCrewAITool(name, description, func)
        self._tools.append(tool)

    def get_crewai_tools(self) -> List[Any]:
        try:
            from crewai import Agent, Task, Crew

            return self._tools
        except ImportError:
            return self._tools

    def create_agent(
        self,
        role: str,
        goal: str,
        backstory: str,
    ) -> Any:
        try:
            from crewai import Agent
            from crewai.tools import Tool

            tools = [
                Tool(
                    name=tool.name,
                    description=tool.description,
                    func=tool.func,
                )
                for tool in self._tools
            ]
            return Agent(role=role, goal=goal, backstory=backstory, tools=tools)
        except ImportError:
            raise ImportError("crewai required")


def mount_aicp(config: Optional[CrewAIConfig] = None) -> AicpCrewAIAdapter:
    return AicpCrewAIAdapter(config)