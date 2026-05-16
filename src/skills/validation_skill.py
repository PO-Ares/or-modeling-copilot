"""Model validation skill."""

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

from src.schemas.modeling_schema import ModelingResult, ValidationResult


def validate_model(model: ModelingResult) -> ValidationResult:
    code = model.model_code or ""
    issues: list[str] = []
    if model.status == "unsupported":
        issues.append("当前问题类型没有可执行的建模模块。")
    if "LpProblem" not in code and model.status != "unsupported":
        issues.append("模型代码中没有创建 PuLP 优化问题。")
    if "prob +=" not in code and model.status != "unsupported":
        issues.append("模型代码中没有明确目标函数或约束。")
    if "solve" not in code and model.status != "unsupported":
        issues.append("模型代码中没有调用求解器。")

    return ValidationResult(
        is_valid=len(issues) == 0,
        issues=issues,
        suggestions=[
            "当前系统采用安全的固定 PuLP 建模模板，适合本地部署、快速演示和稳定求解。",
            "真实业务落地时建议继续采用结构化 JSON 作为中间层，再由后端生成 PuLP 模型，避免直接执行未知代码。",
            "如需支持整数变量、时间窗、路径顺序或选址约束，可继续增加对应建模模块。",
        ],
        confidence=0.92 if not issues else 0.55,
        skill_used="validation_skill",
    )


@tool("validation_skill")
def validation_tool(model_code: str) -> str:
    """Validate whether a PuLP model code block contains basic modeling components."""
    model = ModelingResult(model_description="", model_code=model_code, status="generated", skill_used="external")
    return validate_model(model).model_dump_json(ensure_ascii=False)
