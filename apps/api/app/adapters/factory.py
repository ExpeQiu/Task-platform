from app.adapters.base import BaseAgentAdapter, PullAdapter, PushAdapter
from app.adapters.coze import CozeAdapter
from app.adapters.dify import DifyAdapter
from app.models.entities import AgentAdapter, AdapterProtocol

_TYPE_ALIASES: dict[str, type[BaseAgentAdapter]] = {
    "coze": CozeAdapter,
    "扣子": CozeAdapter,
    "dify": DifyAdapter,
}


def _resolve_type_class(adapter_type: str) -> type[BaseAgentAdapter] | None:
    key = (adapter_type or "").strip().lower()
    return _TYPE_ALIASES.get(key)


def get_adapter(adapter: AgentAdapter) -> BaseAgentAdapter:
    typed = _resolve_type_class(adapter.adapter_type)
    if typed:
        return typed(adapter)
    if adapter.protocol == AdapterProtocol.PULL.value:
        return PullAdapter(adapter)
    return PushAdapter(adapter)
