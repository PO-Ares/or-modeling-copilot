"""Requirement analysis skill."""

from __future__ import annotations

import json
import re
from typing import Dict, Any

try:
    from langchain_core.tools import tool
except Exception:  # pragma: no cover
    def tool(name=None, **kwargs):
        def decorator(func):
            return func
        if callable(name):
            return name
        return decorator

from src.core.config import settings
from src.core.llm_provider import safe_llm_invoke
from src.schemas.modeling_schema import RequirementAnalysis


SUPPORTED_TYPES = {
    "production_planning": "生产计划优化",
    "transportation": "运输分配优化",
    "portfolio": "投资组合优化",
    "unsupported": "暂不支持的问题类型",
}



def _strong_transportation_signal(problem: str) -> bool:
    """Detect supply-demand-cost allocation wording before trusting LLM labels."""
    text = problem.lower()
    has_supply = any(k in text for k in ["供应", "供给", "库存", "supply"])
    has_demand = any(k in text for k in ["需求", "需要", "demand"])
    has_destination = any(k in text for k in ["仓库", "客户", "配送", "运输", "物流", "warehouse", "customer", "transport"])
    has_cost_arc = bool(re.search(r"[A-Za-z0-9一二三四五六七八九十]+\s*(?:到|->|-|至)\s*[A-Za-z0-9一二三四五六七八九十]+\s*(?:成本|费用|运费|cost)?\s*\d", problem, re.I))
    return (has_supply and has_demand and has_destination) or has_cost_arc


def _rule_based_requirement(problem: str) -> RequirementAnalysis:
    text = problem.lower()
    production_keys = ["生产", "产线", "产能", "工厂", "制造", "production", "factory", "line", "capacity"]
    transportation_keys = ["配送", "运输", "物流", "客户", "仓库", "供应", "供给", "库存", "需求", "distribution", "transport", "delivery", "shipping", "supply", "demand"]
    portfolio_keys = ["投资", "收益", "风险", "资产", "portfolio", "return", "risk", "asset"]

    if any(k in text for k in portfolio_keys):
        return RequirementAnalysis(
            problem_type="portfolio",
            display_name=SUPPORTED_TYPES["portfolio"],
            decision_variables=["amount_i: 投资到产品/资产 i 的金额"],
            objective="最大化预期收益",
            constraints=["总预算约束", "风险上限约束", "非负投资约束"],
            clarifications_needed=[],
            confidence=0.88,
            llm_used=False,
            raw_problem=problem,
        )
    if any(k in text for k in transportation_keys):
        return RequirementAnalysis(
            problem_type="transportation",
            display_name=SUPPORTED_TYPES["transportation"],
            decision_variables=["x_ij: 从配送中心 i 分配给客户组 j 的数量"],
            objective="最小化总运输/配送成本",
            constraints=["配送中心供给约束", "客户需求约束", "非负运输量约束"],
            clarifications_needed=["若要扩展为 VRP，需要客户坐标、车辆容量、时间窗和路径顺序信息。"],
            confidence=0.84,
            llm_used=False,
            raw_problem=problem,
        )
    if any(k in text for k in production_keys):
        return RequirementAnalysis(
            problem_type="production_planning",
            display_name=SUPPORTED_TYPES["production_planning"],
            decision_variables=["x_lp: 产线 l 生产产品 p 的数量"],
            objective="最小化总生产成本",
            constraints=["产品需求约束", "产线产能约束", "非负生产量约束"],
            clarifications_needed=[],
            confidence=0.86,
            llm_used=False,
            raw_problem=problem,
        )

    return RequirementAnalysis(
        problem_type="unsupported",
        display_name=SUPPORTED_TYPES["unsupported"],
        decision_variables=[],
        objective="无法从输入中稳定识别可求解的优化目标",
        constraints=[],
        clarifications_needed=["请说明问题类型、目标函数、决策变量、约束条件和关键参数。"],
        confidence=0.30,
        llm_used=False,
        raw_problem=problem,
    )


def _extract_json(text: str) -> Dict[str, Any] | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


async def analyze_requirement(problem: str) -> RequirementAnalysis:
    fallback = _rule_based_requirement(problem)
    if not settings.use_llm_classification:
        return fallback

    prompt = f"""
Classify the operations research problem into exactly one of:
production_planning, transportation, portfolio, unsupported.
Return JSON only with: problem_type, display_name, decision_variables, objective, constraints, clarifications_needed, confidence.
Use Chinese for display_name, objective, constraints, clarifications_needed.

User problem:
{problem}
"""
    llm_text = await safe_llm_invoke(prompt, temperature=0.0)
    data = _extract_json(llm_text or "")
    if not data:
        return fallback

    # If the text clearly describes supply-demand-cost allocation, keep it as transportation.
    # This avoids LLMs confusing 工厂+仓库 cases with production planning.
    if _strong_transportation_signal(problem):
        data["problem_type"] = "transportation"
        data["display_name"] = SUPPORTED_TYPES["transportation"]

    try:
        problem_type = str(data.get("problem_type", fallback.problem_type)).strip()
        if problem_type not in SUPPORTED_TYPES:
            problem_type = fallback.problem_type
        return RequirementAnalysis(
            problem_type=problem_type,
            display_name=str(data.get("display_name") or SUPPORTED_TYPES.get(problem_type, fallback.display_name)),
            decision_variables=list(data.get("decision_variables") or fallback.decision_variables),
            objective=str(data.get("objective") or fallback.objective),
            constraints=list(data.get("constraints") or fallback.constraints),
            clarifications_needed=list(data.get("clarifications_needed") or fallback.clarifications_needed),
            confidence=float(data.get("confidence", fallback.confidence)),
            llm_used=True,
            raw_problem=problem,
        )
    except Exception:
        return fallback


@tool("requirement_analysis_skill")
def requirement_analysis_tool(problem: str) -> str:
    """Classify an operations research problem and extract variables, objective, constraints, and problem type."""
    result = _rule_based_requirement(problem)
    return result.model_dump_json(ensure_ascii=False)
