from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from .bus import AgentCommunicationBus

class Agent(BaseModel):
    id: str
    type: str
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)

class AgentHierarchy(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    
    def __init__(self, bus: Optional[AgentCommunicationBus] = None, **data):
        super().__init__(**data)
        object.__setattr__(self, 'bus', bus or AgentCommunicationBus())
        object.__setattr__(self, 'agents', {})

    def create_agent(self, id: str, agent_type: str, parent_id: Optional[str] = None) -> Agent:
        if not hasattr(self, 'agents'):
            object.__setattr__(self, 'agents', {})
        agent = Agent(id=id, type=agent_type, parent_id=parent_id)
        self.agents[id] = agent
        if parent_id and parent_id in self.agents:
            self.agents[parent_id].children.append(id)
        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        if not hasattr(self, 'agents'):
            return None
        return self.agents.get(agent_id)

    def get_children(self, agent_id: str) -> List[Agent]:
        agent = self.get_agent(agent_id)
        if not agent:
            return []
        return [self.agents[cid] for cid in agent.children if cid in self.agents]
