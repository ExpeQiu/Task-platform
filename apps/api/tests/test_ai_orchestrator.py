"""AI 编排 Mock 测试"""

from app.services.ai_orchestrator import _mock_chat


def test_mock_scrape_and_summarize():
    resp = _mock_chat("抓取竞品数据并生成分析报告", ["OpenClaw", "Hermes"])
    assert resp.dag is not None
    assert len(resp.dag.nodes) >= 4
    types = {n.type for n in resp.dag.nodes}
    assert "start" in types
    assert "agent" in types
    assert "end" in types


def test_mock_help():
    resp = _mock_chat("帮助", [])
    assert resp.dag is None
    assert "抓取" in resp.reply
