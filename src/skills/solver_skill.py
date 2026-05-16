"""PuLP solver skill."""

from __future__ import annotations

from typing import Any, Dict

try:
    import pulp
except Exception:  # pragma: no cover
    pulp = None

try:
    from langchain_core.tools import tool
except Exception:  # pragma: no cover
    def tool(name=None, **kwargs):
        def decorator(func):
            return func
        if callable(name):
            return name
        return decorator

from src.schemas.modeling_schema import ModelingResult, SolveResult


def solve_model(model: ModelingResult) -> SolveResult:
    if model.status == "unsupported":
        return SolveResult(
            status="unsupported",
            objective_value=None,
            solution={},
            explanation="当前问题类型还没有可执行模板。可以补充新的 modeling skill 后再求解。",
            sensitivity_analysis={},
        )

    if pulp is None:
        return _fallback_solve(model.model_code)

    namespace: Dict[str, Any] = {"pulp": pulp, "__builtins__": {"__import__": __import__}}
    try:
        exec(model.model_code, namespace)
        prob = namespace.get("prob")
        if prob is None:
            raise ValueError("No variable named 'prob' was found in the model code.")
        status = pulp.LpStatus.get(prob.status, str(prob.status))
        objective_value = pulp.value(prob.objective)
        solution = {v.name: v.varValue for v in prob.variables()}
        direction = "最大" if prob.sense == pulp.LpMaximize else "最小"
        return SolveResult(
            status=status,
            objective_value=objective_value,
            solution=solution,
            explanation=f"求解状态为 {status}。当前模型的{direction}目标值为 {objective_value:.2f}。",
            sensitivity_analysis={
                "说明": "当前版本返回基础求解结果；完整敏感性分析需要结合对偶值、松弛量或商业求解器输出。",
                "下一步": "可扩展约束 shadow price、slack 和参数扰动分析。",
            },
        )
    except Exception as exc:
        return SolveResult(
            status="failed",
            objective_value=None,
            solution={},
            explanation=f"模型求解失败：{exc}",
            sensitivity_analysis={},
        )


def _fallback_solve(model_code: str) -> SolveResult:
    if "Portfolio_Optimization" in model_code:
        return SolveResult(
            status="demo_fallback_no_pulp",
            objective_value=100000.0,
            solution={"amount_A": 0.0, "amount_B": 500000.0, "amount_C": 500000.0, "amount_D": 0.0},
            explanation="当前环境未安装 PuLP，返回演示解。安装依赖后将调用 PuLP/CBC 真实求解。",
            sensitivity_analysis={"说明": "演示模式不提供真实敏感性分析。"},
        )
    if "Transportation_Planning" in model_code:
        return SolveResult(
            status="demo_fallback_no_pulp",
            objective_value=4750.0,
            solution={
                "ship_DC1_Customer_Group_1": 20.0,
                "ship_DC1_Customer_Group_2": 170.0,
                "ship_DC1_Customer_Group_3": 10.0,
                "ship_DC2_Customer_Group_3": 150.0,
                "ship_DC3_Customer_Group_1": 160.0,
                "ship_DC3_Customer_Group_3": 20.0,
            },
            explanation="当前环境未安装 PuLP，返回演示解。安装依赖后将调用 PuLP/CBC 真实求解。",
            sensitivity_analysis={"说明": "演示模式不提供真实敏感性分析。"},
        )
    return SolveResult(
        status="demo_fallback_no_pulp",
        objective_value=143000.0,
        solution={"produce_A": 500.0, "produce_B": 400.0, "produce_C": 300.0},
        explanation="当前环境未安装 PuLP，返回演示解。安装依赖后将调用 PuLP/CBC 真实求解。",
        sensitivity_analysis={"说明": "演示模式不提供真实敏感性分析。"},
    )


@tool("solver_skill")
def solver_tool(model_code: str) -> str:
    """Solve a generated PuLP model and return objective value and variable assignments."""
    model = ModelingResult(model_description="", model_code=model_code, status="generated", skill_used="external")
    return solve_model(model).model_dump_json(ensure_ascii=False)
