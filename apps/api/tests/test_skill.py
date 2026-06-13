from app.services.skill_service import SkillService
from app.models.entities import Skill


def test_apply_to_objective():
    skill = Skill(name="report", instructions="输出 Markdown 报告，包含摘要和结论。")
    svc = SkillService(db=None)  # type: ignore
    result = svc.apply_to_objective(skill, "生成竞品分析")
    assert "report" in result
    assert "Markdown" in result
