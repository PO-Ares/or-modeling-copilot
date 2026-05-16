"""Supervisor agent for the LangChain-based skills-agent architecture."""

from __future__ import annotations

from typing import Callable, Dict

from src.schemas.modeling_schema import (
    AgentTraceStep,
    PipelineResult,
    RequirementAnalysis,
    ModelingResult,
)
from src.skills.requirement_skill import analyze_requirement
from src.skills.parameter_extraction_skill import extract_parameters
from src.skills.modeling_skills import (
    build_production_planning_model,
    build_transportation_model,
    build_portfolio_model,
    build_unsupported_model,
)
from src.skills.validation_skill import validate_model
from src.skills.solver_skill import solve_model
from src.skills.interpretation_skill import interpret_result


class SupervisorAgent:
    """Coordinates OR skills in a local-deployable skills-agent workflow.

    The current implementation uses LangChain for the optional LLM classification
    layer and keeps model generation/solving deterministic for stability.
    """

    def __init__(self) -> None:
        self.modeling_skills: Dict[str, Callable[[RequirementAnalysis], ModelingResult]] = {
            "production_planning": build_production_planning_model,
            "transportation": build_transportation_model,
            "portfolio": build_portfolio_model,
            "unsupported": build_unsupported_model,
        }

    async def run(self, problem_statement: str) -> PipelineResult:
        trace: list[AgentTraceStep] = []

        requirement = await analyze_requirement(problem_statement)
        trace.append(
            AgentTraceStep(
                step="1",
                skill="需求识别",
                status="完成",
                summary=f"已识别为：{requirement.display_name}。",
            )
        )

        extraction = await extract_parameters(requirement)
        requirement.intent = extraction.intent
        requirement.slots = extraction.slots
        requirement.missing_slots = extraction.missing_slots
        requirement.structured_parameters = extraction.structured_parameters
        requirement.extraction_method = extraction.extraction_method
        # If all required parameters have been extracted, remove stale LLM clarification prompts.
        # This avoids showing messages such as "请提供运输成本表格" after the cost table
        # has already been parsed and the model has been solved successfully.
        if not extraction.missing_slots:
            requirement.clarifications_needed = []
        slot_name_map = {
            "lines": "产线/产能与成本信息",
            "demands": "需求信息",
            "costs": "运输成本表",
            "supplies": "供应量信息",
            "budget": "投资预算",
            "assets": "投资产品信息",
            "risk_limit": "风险上限",
        }
        missing_cn = [slot_name_map.get(x, x) for x in extraction.missing_slots]
        extracted_summary = "关键参数已完成结构化抽取。" if not missing_cn else "仍需补充：" + "、".join(missing_cn) + "。"
        trace.append(
            AgentTraceStep(
                step="2",
                skill="参数抽取",
                status="完成" if not extraction.missing_slots else "待补充",
                summary=extracted_summary,
            )
        )

        modeling_skill = self.modeling_skills.get(requirement.problem_type, build_unsupported_model)
        model = modeling_skill(requirement)
        trace.append(
            AgentTraceStep(
                step="3",
                skill="模型构建",
                status="已生成" if model.status == "generated" else model.status,
                summary=model.model_description,
            )
        )

        validation = validate_model(model)
        trace.append(
            AgentTraceStep(
                step="4",
                skill="模型验证",
                status="通过" if validation.is_valid else "需修改",
                summary="模型基础检查通过。" if validation.is_valid else "模型存在问题，需要补充或修改。",
            )
        )

        solve_result = solve_model(model)
        solve_result.explanation = interpret_result(requirement, solve_result)
        trace.append(
            AgentTraceStep(
                step="5",
                skill="优化求解",
                status=solve_result.status,
                summary=solve_result.explanation or "求解完成。",
            )
        )

        return PipelineResult(
            requirement_analysis=requirement,
            modeling_result=model,
            validation_result=validation,
            solve_result=solve_result,
            agent_trace=trace,
        )
