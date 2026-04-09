from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentCommunicationBus(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    subscriptions: dict[str, list[Callable]] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        object.__setattr__(self, 'subscriptions', {})

    def subscribe(self, topic: str, callback: Callable):
        if not hasattr(self, 'subscriptions'):
            object.__setattr__(self, 'subscriptions', {})
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(callback)

    def publish(self, topic: str, message: Any):
        if hasattr(self, 'subscriptions') and topic in self.subscriptions:
            for callback in self.subscriptions[topic]:
                callback(message)

    def unsubscribe(self, topic: str, callback: Callable):
        if hasattr(self, 'subscriptions') and topic in self.subscriptions:
            self.subscriptions[topic].remove(callback)
