"""Result interpretation skill."""

from __future__ import annotations

try:
    from langchain_core.tools import tool
except Exception:  # pragma: no cover
    def tool(name=None, **kwargs):
        def decorator(func):
            return func
        if callable(name):
            return name
        return decorator

from src.schemas.modeling_schema import RequirementAnalysis, SolveResult


def interpret_result(requirement: RequirementAnalysis, solve_result: SolveResult) -> str:
    if solve_result.status in {"unsupported", "failed"}:
        return solve_result.explanation or "当前模型未能成功求解。"
    if requirement.problem_type == "production_planning":
        return f"该生产计划模型已完成求解。系统建议按照最优方案安排各产品生产，总成本约为 {solve_result.objective_value:.2f}。"
    if requirement.problem_type == "transportation":
        return f"该运输分配模型已完成求解。系统给出了各供应点到需求点的运输量，总运输成本约为 {solve_result.objective_value:.2f}。"
    if requirement.problem_type == "portfolio":
        return f"该投资组合模型已完成求解。在风险限制下，最大预期收益约为 {solve_result.objective_value:.2f}。"
    return solve_result.explanation or "模型已完成求解。"


@tool("result_interpretation_skill")
def interpretation_tool(text: str) -> str:
    """Explain an optimization result in user-friendly language."""
    return "已生成面向业务用户的结果解释。"
