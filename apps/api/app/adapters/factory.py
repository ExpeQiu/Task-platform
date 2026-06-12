from app.adapters.base import BaseAgentAdapter, PullAdapter, PushAdapter
from app.models.entities import AgentAdapter, AdapterProtocol


def get_adapter(adapter: AgentAdapter) -> BaseAgentAdapter:
    if adapter.protocol == AdapterProtocol.PULL.value:
        return PullAdapter(adapter)
    return PushAdapter(adapter)
