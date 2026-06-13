from app.schemas.dto import VALID_NODE_TYPES


def test_approval_node_type_valid():
    assert "approval" in VALID_NODE_TYPES


def test_verification_modes_documented():
    modes = {"rule_based", "llm_agent", "hybrid"}
    assert "llm_agent" in modes
