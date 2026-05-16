"""Domain modeling skills with lightweight parameter extraction.

The templates are still intentionally controlled, but they now read common numbers
from the user's prompt instead of always returning the same fixed model.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

try:
    from langchain_core.tools import tool
except Exception:  # pragma: no cover
    def tool(name=None, **kwargs):
        def decorator(func):
            return func
        if callable(name):
            return name
        return decorator

from src.schemas.modeling_schema import RequirementAnalysis, ModelingResult


def _num(text: str) -> float | None:
    if text is None:
        return None
    s = text.replace(",", "").replace("，", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def _safe_name(name: str) -> str:
    name = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]+", "_", name).strip("_")
    return name or "item"




def _normalize_arrow_costs(raw_costs: Dict) -> Dict[Tuple[str, str], float]:
    """Convert {'A->X': 2} or {(A,X):2} cost data into tuple-key dict."""
    costs: Dict[Tuple[str, str], float] = {}
    if not isinstance(raw_costs, dict):
        return costs
    for key, value in raw_costs.items():
        val = _num(str(value)) if not isinstance(value, (int, float)) else float(value)
        if val is None:
            continue
        if isinstance(key, tuple) and len(key) == 2:
            costs[(str(key[0]), str(key[1]))] = val
        elif isinstance(key, str) and "->" in key:
            a, b = key.split("->", 1)
            costs[(a.strip(), b.strip())] = val
    return costs


def _balance_transportation(
    supplies: Dict[str, float],
    demands: Dict[str, float],
    costs: Dict[Tuple[str, str], float],
) -> Tuple[Dict[str, float], Dict[str, float], Dict[Tuple[str, str], float], List[str]]:
    """Add dummy source/destination when supply and demand are unbalanced.

    This is a lightweight self-correction step: it prevents common infeasibility
    caused by total supply not matching total demand and makes the assumption
    explicit in the model description.
    """
    notes: List[str] = []
    total_supply = sum(float(v) for v in supplies.values())
    total_demand = sum(float(v) for v in demands.values())
    max_cost = max(costs.values()) if costs else 1.0
    penalty = max_cost * 10
    if total_supply > total_demand:
        dummy = "Dummy_Demand"
        demands[dummy] = total_supply - total_demand
        for i in supplies:
            costs[(i, dummy)] = 0.0
        notes.append(f"总供应量大于总需求量，已自动添加虚拟需求节点，吸收剩余供应 {total_supply - total_demand:.2f}。")
    elif total_demand > total_supply:
        dummy = "Dummy_Source"
        supplies[dummy] = total_demand - total_supply
        for j in demands:
            costs[(dummy, j)] = penalty
        notes.append(f"总需求量大于总供应量，已自动添加虚拟供应节点，补足缺口 {total_demand - total_supply:.2f}，并设置惩罚成本 {penalty:.2f}。")
    return supplies, demands, costs, notes


def _extract_production(problem: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    lines: Dict[str, Dict[str, float]] = {}
    # Matches: 产线1每月产能1000单位，成本100元/单位
    for m in re.finditer(r"产线\s*([0-9一二三四五六七八九十A-Za-z]+).*?产能\s*([0-9,.]+).*?成本\s*([0-9,.]+)", problem, re.S):
        idx, cap, cost = m.group(1), _num(m.group(2)), _num(m.group(3))
        if cap is not None and cost is not None:
            lines[f"Line_{idx}"] = {"capacity": cap, "cost": cost}
    # English: Line 1: capacity = 1000 cost = 100
    for m in re.finditer(r"Line\s*([0-9A-Za-z]+).*?capacity\s*[=:：]?\s*([0-9,.]+).*?cost\s*[=:：]?\s*([0-9,.]+)", problem, re.I | re.S):
        idx, cap, cost = m.group(1), _num(m.group(2)), _num(m.group(3))
        if cap is not None and cost is not None:
            lines[f"Line_{idx}"] = {"capacity": cap, "cost": cost}

    demands: Dict[str, float] = {}
    # A产品500单位 / A = 500 / A产品需求500
    for m in re.finditer(r"([A-Za-z\u4e00-\u9fff]{1,8})\s*(?:产品)?\s*(?:需求|=|：|:)?\s*([0-9,.]+)\s*(?:单位|件|个)?", problem):
        product, val = m.group(1), _num(m.group(2))
        if val is not None and product not in {"产线", "成本", "产能", "需求"}:
            # Keep short product names and avoid line/cost captures.
            if len(product) <= 4:
                demands[_safe_name(product)] = val

    # If noisy extraction found too many words, prefer common A/B/C product pattern.
    abc: Dict[str, float] = {}
    for m in re.finditer(r"([A-Z])\s*(?:产品)?\s*([0-9,.]+)\s*(?:单位|件|个)?", problem):
        val = _num(m.group(2))
        if val is not None:
            abc[m.group(1)] = val
    if abc:
        demands = abc

    if not lines:
        lines = {
            "Line_1": {"capacity": 1000, "cost": 100},
            "Line_2": {"capacity": 800, "cost": 120},
            "Line_3": {"capacity": 600, "cost": 150},
        }
    if not demands:
        demands = {"A": 500, "B": 400, "C": 300}
    return lines, demands


def _extract_portfolio(problem: str) -> Tuple[float, Dict[str, Dict[str, float]], float]:
    budget = 1_000_000.0
    m_budget = re.search(r"([0-9,.]+)\s*(?:万)?\s*(?:元|美元|dollars|budget|预算)", problem, re.I)
    if m_budget:
        val = _num(m_budget.group(1))
        if val is not None:
            budget = val * 10000 if "万" in m_budget.group(0) else val

    assets: Dict[str, Dict[str, float]] = {}
    for m in re.finditer(r"产品\s*([A-Za-z0-9]+).*?收益\s*([0-9,.]+)\s*%.*?风险(?:等级)?\s*([0-9,.]+)", problem, re.S):
        name, ret, risk = m.group(1), _num(m.group(2)), _num(m.group(3))
        if ret is not None and risk is not None:
            assets[f"Asset_{name}"] = {"return": ret / 100, "risk": risk}
    for m in re.finditer(r"Asset\s*([A-Za-z0-9]+).*?return\s*[=:：]?\s*([0-9,.]+)\s*%?.*?risk\s*[=:：]?\s*([0-9,.]+)", problem, re.I | re.S):
        name, ret, risk = m.group(1), _num(m.group(2)), _num(m.group(3))
        if ret is not None and risk is not None:
            assets[f"Asset_{name}"] = {"return": ret / 100 if ret > 1 else ret, "risk": risk}

    risk_limit = 2.0
    m_risk = re.search(r"风险(?:等级)?(?:不超过|<=|小于等于|限制|上限)\s*([0-9,.]+)", problem)
    if m_risk and _num(m_risk.group(1)) is not None:
        risk_limit = _num(m_risk.group(1)) or risk_limit

    if not assets:
        assets = {
            "Asset_A": {"return": 0.10, "risk": 2},
            "Asset_B": {"return": 0.08, "risk": 1},
            "Asset_C": {"return": 0.12, "risk": 3},
            "Asset_D": {"return": 0.06, "risk": 1},
        }
    return budget, assets, risk_limit


def _extract_transportation(problem: str, structured: Dict | None = None):
    structured = structured or {}
    supplies = structured.get("supplies") or {}
    demands = structured.get("demands") or {}
    costs = _normalize_arrow_costs(structured.get("costs") or {})

    supplies = {str(k): float(v) for k, v in supplies.items()} if isinstance(supplies, dict) else {}
    demands = {str(k): float(v) for k, v in demands.items()} if isinstance(demands, dict) else {}

    # Fall back to the stable demo template if key slots are missing.
    if not supplies:
        supplies = {"DC1": 200, "DC2": 150, "DC3": 180}
    if not demands:
        demands = {"Customer_Group_1": 180, "Customer_Group_2": 170, "Customer_Group_3": 180}
    if not costs:
        costs = {
            ("DC1", "Customer_Group_1"): 10, ("DC1", "Customer_Group_2"): 12, ("DC1", "Customer_Group_3"): 15,
            ("DC2", "Customer_Group_1"): 11, ("DC2", "Customer_Group_2"): 9,  ("DC2", "Customer_Group_3"): 13,
            ("DC3", "Customer_Group_1"): 8,  ("DC3", "Customer_Group_2"): 10, ("DC3", "Customer_Group_3"): 9,
        }
    else:
        # Ensure missing arcs receive a transparent high penalty instead of crashing.
        max_cost = max(costs.values()) if costs else 1.0
        penalty = max_cost * 10
        for i in supplies:
            for j in demands:
                costs.setdefault((i, j), penalty)

    supplies, demands, costs, notes = _balance_transportation(supplies, demands, costs)
    return supplies, demands, costs, notes


def build_production_planning_model(requirement: RequirementAnalysis) -> ModelingResult:
    lines, demands = _extract_production(requirement.raw_problem)
    if requirement.structured_parameters.get("lines"):
        lines = requirement.structured_parameters["lines"]
    if requirement.structured_parameters.get("demands") and requirement.problem_type == "production_planning":
        demands = requirement.structured_parameters["demands"]
    model_code = f'''import pulp

lines = {lines!r}
demands = {demands!r}

prob = pulp.LpProblem("Production_Planning", pulp.LpMinimize)

x = pulp.LpVariable.dicts("produce", [(l, p) for l in lines for p in demands], lowBound=0)

prob += pulp.lpSum(lines[l]["cost"] * x[l, p] for l in lines for p in demands), "Total_Cost"

for p in demands:
    prob += pulp.lpSum(x[l, p] for l in lines) >= demands[p], f"Demand_{{p}}"

for l in lines:
    prob += pulp.lpSum(x[l, p] for p in demands) <= lines[l]["capacity"], f"Capacity_{{l}}"

prob.solve(pulp.PULP_CBC_CMD(msg=0))
'''
    return ModelingResult(
        model_description=f"已构建生产计划优化模型：识别到 {len(lines)} 条产线和 {len(demands)} 个产品需求，在产能约束下最小化总生产成本。",
        model_code=model_code,
        status="generated",
        skill_used="production_planning_skill",
    )


def build_transportation_model(requirement: RequirementAnalysis) -> ModelingResult:
    supplies, demands, costs, correction_notes = _extract_transportation(requirement.raw_problem, requirement.structured_parameters)
    model_code = f'''import pulp

supplies = {supplies!r}
demands = {demands!r}
costs = {costs!r}

prob = pulp.LpProblem("Transportation_Planning", pulp.LpMinimize)

x = pulp.LpVariable.dicts("ship", costs.keys(), lowBound=0)

prob += pulp.lpSum(costs[i, j] * x[i, j] for (i, j) in costs), "Total_Transportation_Cost"

for i in supplies:
    prob += pulp.lpSum(x[i, j] for j in demands if (i, j) in costs) <= supplies[i], f"Supply_{{i}}"
for j in demands:
    prob += pulp.lpSum(x[i, j] for i in supplies if (i, j) in costs) >= demands[j], f"Demand_{{j}}"

prob.solve(pulp.PULP_CBC_CMD(msg=0))
'''
    return ModelingResult(
        model_description=(
            f"已根据供应量、需求量和运输成本构建运输分配优化模型，在供需约束下最小化总运输成本。"
            + (" 自动修正：" + "；".join(correction_notes) if correction_notes else "")
        ),
        model_code=model_code,
        status="generated",
        skill_used="transportation_modeling_skill",
    )


def build_portfolio_model(requirement: RequirementAnalysis) -> ModelingResult:
    budget, assets, risk_limit = _extract_portfolio(requirement.raw_problem)
    if requirement.structured_parameters.get("budget"):
        budget = float(requirement.structured_parameters["budget"])
    if requirement.structured_parameters.get("assets"):
        assets = requirement.structured_parameters["assets"]
    if requirement.structured_parameters.get("risk_limit"):
        risk_limit = float(requirement.structured_parameters["risk_limit"])
    model_code = f'''import pulp

budget = {budget!r}
assets = {assets!r}
risk_limit = {risk_limit!r}

prob = pulp.LpProblem("Portfolio_Optimization", pulp.LpMaximize)

amount = pulp.LpVariable.dicts("amount", assets.keys(), lowBound=0)

prob += pulp.lpSum(assets[a]["return"] * amount[a] for a in assets), "Expected_Return"

prob += pulp.lpSum(amount[a] for a in assets) == budget, "Budget"
prob += pulp.lpSum(assets[a]["risk"] * amount[a] for a in assets) <= risk_limit * budget, "Average_Risk_Limit"

prob.solve(pulp.PULP_CBC_CMD(msg=0))
'''
    return ModelingResult(
        model_description=f"已构建投资组合优化模型：识别到 {len(assets)} 个投资产品，预算为 {budget:.0f}，平均风险限制为 {risk_limit}，目标是最大化预期收益。",
        model_code=model_code,
        status="generated",
        skill_used="portfolio_modeling_skill",
    )


def build_unsupported_model(requirement: RequirementAnalysis) -> ModelingResult:
    return ModelingResult(
        model_description="当前输入没有被稳定识别为可自动求解的生产计划、配送分配或投资组合问题。请补充目标函数、决策变量、约束条件和参数。",
        model_code="# Unsupported problem type in the current version.\n",
        status="unsupported",
        skill_used="unsupported_problem_skill",
    )


@tool("production_planning_modeling_skill")
def production_planning_tool(_: str = "") -> str:
    """Build a PuLP production planning model from recognized production parameters."""
    dummy = RequirementAnalysis(problem_type="production_planning", display_name="生产计划", decision_variables=[], objective="", constraints=[])
    return build_production_planning_model(dummy).model_dump_json(ensure_ascii=False)


@tool("transportation_modeling_skill")
def transportation_tool(_: str = "") -> str:
    """Build a PuLP transportation allocation model for distribution cost minimization."""
    dummy = RequirementAnalysis(problem_type="transportation", display_name="配送分配", decision_variables=[], objective="", constraints=[])
    return build_transportation_model(dummy).model_dump_json(ensure_ascii=False)


@tool("portfolio_modeling_skill")
def portfolio_tool(_: str = "") -> str:
    """Build a PuLP portfolio optimization model from budget, return, and risk parameters."""
    dummy = RequirementAnalysis(problem_type="portfolio", display_name="投资组合", decision_variables=[], objective="", constraints=[])
    return build_portfolio_model(dummy).model_dump_json(ensure_ascii=False)
