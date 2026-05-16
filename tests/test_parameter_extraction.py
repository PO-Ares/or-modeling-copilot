import asyncio

from src.agent.supervisor import SupervisorAgent
from src.schemas.modeling_schema import RequirementAnalysis
from src.skills.parameter_extraction_skill import extract_parameters


def test_transportation_structured_extraction():
    req = RequirementAnalysis(
        problem_type="transportation",
        display_name="配送分配优化",
        decision_variables=[],
        objective="min cost",
        constraints=[],
        raw_problem="Transportation problem. supply: A=50, B=70; demand: X=30, Y=40, Z=50; cost_matrix=[[2,4,5],[3,1,7]].",
    )
    result = asyncio.run(extract_parameters(req))
    assert result.intent == "transportation"
    assert result.structured_parameters["supplies"]["A"] == 50
    assert result.structured_parameters["demands"]["Z"] == 50
    assert result.structured_parameters["costs"]["B->Y"] == 1
    assert result.missing_slots == []


def test_agent_pipeline_contains_parameter_extraction_step():
    result = asyncio.run(SupervisorAgent().run(
        "Transportation problem. supply: A=50, B=70; demand: X=30, Y=40, Z=50; cost_matrix=[[2,4,5],[3,1,7]]."
    ))
    skills = [step.skill for step in result.agent_trace]
    assert "参数抽取" in skills
    assert result.requirement_analysis.intent == "transportation"
