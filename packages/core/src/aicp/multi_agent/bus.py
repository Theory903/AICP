from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field, ConfigDict

class AgentCommunicationBus(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    
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
