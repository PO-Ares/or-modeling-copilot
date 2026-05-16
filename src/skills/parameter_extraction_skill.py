"""Intent, slot filling, and structured parameter extraction skill.

This module upgrades the MVP from simple keyword routing toward a safer
"natural language -> JSON -> deterministic solver" workflow. It deliberately
keeps model execution controlled: the LLM may produce JSON parameters, but it
never produces executable Python code.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Tuple

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
from src.schemas.modeling_schema import ParameterExtractionResult, RequirementAnalysis


REQUIRED_SLOTS = {
    "production_planning": ["lines", "demands"],
    "transportation": ["supplies", "demands", "costs"],
    "portfolio": ["budget", "assets", "risk_limit"],
}


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


def _to_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    text = str(value).replace(",", "").replace("，", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    num = float(m.group(0))
    if "万" in text:
        num *= 10000
    return num


def _parse_mapping(text: str, labels: List[str]) -> Dict[str, float]:
    """Parse mappings like 'A=50, B:70' or 'A 50 B 70'."""
    result: Dict[str, float] = {}
    for label in labels:
        pattern = rf"(?:{re.escape(label)}|{re.escape(label.upper())})\s*(?:=|:|：)?\s*([0-9,.]+)"
        m = re.search(pattern, text, flags=re.I)
        if m:
            val = _to_number(m.group(1))
            if val is not None:
                result[label] = val
    return result


def _find_section(text: str, names: List[str]) -> str:
    joined = "|".join(map(re.escape, names))
    m = re.search(rf"(?:{joined})\s*(?:=|:|：)?\s*([^;；\n]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_cost_matrix(text: str, sources: List[str], destinations: List[str]) -> Dict[Tuple[str, str], float]:
    costs: Dict[Tuple[str, str], float] = {}

    # Pattern 1: A-X=2, A-Y=4, B-X=3
    for i in sources:
        for j in destinations:
            patterns = [
                rf"{re.escape(i)}\s*(?:-|->|到|to)\s*{re.escape(j)}\s*(?:=|:|：)?\s*([0-9,.]+)",
                rf"{re.escape(j)}\s*(?:<-|来自|from)\s*{re.escape(i)}\s*(?:=|:|：)?\s*([0-9,.]+)",
            ]
            for p in patterns:
                m = re.search(p, text, flags=re.I)
                if m:
                    val = _to_number(m.group(1))
                    if val is not None:
                        costs[(i, j)] = val
                        break

    # Pattern 2: cost_matrix=[[2,4,5],[3,1,7]]
    m = re.search(r"cost(?:_matrix)?\s*(?:=|:|：)\s*(\[\s*\[.*?\]\s*\])", text, flags=re.I | re.S)
    if m:
        try:
            matrix = ast.literal_eval(m.group(1))
            for r, i in enumerate(sources):
                for c, j in enumerate(destinations):
                    if r < len(matrix) and c < len(matrix[r]):
                        val = _to_number(matrix[r][c])
                        if val is not None:
                            costs[(i, j)] = val
        except Exception:
            pass
    return costs



def _normalize_cn_label(prefix: str, raw: str) -> str:
    """Return clean labels such as A/B/X/Y instead of internal demo names."""
    raw = str(raw).strip()
    cn_nums = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
    raw = cn_nums.get(raw, raw)
    return raw if re.fullmatch(r"[A-Za-z0-9_]+", raw) else f"{prefix}_{raw}"


def _extract_named_values(problem: str, entity_words: list[str], value_words: list[str]) -> Dict[str, float]:
    """Extract patterns like 工厂A供应20件 / 仓库X需求40件."""
    entities = "|".join(map(re.escape, entity_words))
    values = "|".join(map(re.escape, value_words))
    out: Dict[str, float] = {}
    pattern = rf"(?:{entities})\s*([A-Za-z0-9一二三四五六七八九十_]+)\s*(?:的)?\s*(?:{values})\s*(?:为|是|=|:|：)?\s*([0-9,.]+)"
    for m in re.finditer(pattern, problem, flags=re.I):
        val = _to_number(m.group(2))
        if val is not None:
            out[_normalize_cn_label("N", m.group(1))] = val
    return out

def _rule_extract_transportation(problem: str) -> Dict[str, Any]:
    """Rule-based extraction for Chinese/English transportation allocation problems."""
    supply_section = _find_section(problem, ["supply", "supplies", "供应", "供给", "库存"])
    demand_section = _find_section(problem, ["demand", "demands", "需求"])

    # Prefer explicit Chinese entity patterns.
    supplies = _extract_named_values(problem, ["工厂", "配送中心", "仓库", "供应点", "source", "dc"], ["供应", "供给", "库存", "supply"])
    demands = _extract_named_values(problem, ["仓库", "客户", "需求点", "门店", "destination", "customer"], ["需求", "需要", "demand"])

    # English / compact mapping fallback: supply A=50, B=70; demand X=30, Y=40
    if not supplies:
        source_labels = re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", supply_section)
        supplies = _parse_mapping(supply_section, source_labels)
    if not demands:
        dest_labels = re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", demand_section)
        demands = _parse_mapping(demand_section, dest_labels)

    source_labels = list(supplies.keys())
    dest_labels = list(demands.keys())

    # Costs can use A到X, A-X, A->X. Labels may be A/X even if entity names use 工厂A/仓库X.
    costs: Dict[Tuple[str, str], float] = {}
    for i in source_labels:
        for j in dest_labels:
            raw_i = re.sub(r"^(工厂|配送中心|仓库|source|dc|N_)", "", i, flags=re.I)
            raw_j = re.sub(r"^(仓库|客户|需求点|destination|customer|N_)", "", j, flags=re.I)
            patterns = [
                rf"{re.escape(i)}\s*(?:-|->|到|至|to)\s*{re.escape(j)}\s*(?:成本|费用|运费|cost)?\s*(?:=|:|：)?\s*([0-9,.]+)",
                rf"{re.escape(raw_i)}\s*(?:-|->|到|至|to)\s*{re.escape(raw_j)}\s*(?:成本|费用|运费|cost)?\s*(?:=|:|：)?\s*([0-9,.]+)",
                rf"{re.escape(i)}\s*(?:到|至)\s*{re.escape(j)}\s*(?:的)?(?:运输)?(?:成本|费用|运费)\s*(?:为|是|=|:|：)?\s*([0-9,.]+)",
                rf"{re.escape(raw_i)}\s*(?:到|至)\s*{re.escape(raw_j)}\s*(?:的)?(?:运输)?(?:成本|费用|运费)\s*(?:为|是|=|:|：)?\s*([0-9,.]+)",
            ]
            for p in patterns:
                m = re.search(p, problem, flags=re.I)
                if m:
                    val = _to_number(m.group(1))
                    if val is not None:
                        costs[(i, j)] = val
                        break

    if not costs and source_labels and dest_labels:
        costs = _extract_cost_matrix(problem, source_labels, dest_labels)

    params: Dict[str, Any] = {}
    if supplies:
        params["supplies"] = supplies
    if demands:
        params["demands"] = demands
    if costs:
        params["costs"] = {f"{i}->{j}": v for (i, j), v in costs.items()}
    return params

def _rule_extract_production(problem: str) -> Dict[str, Any]:
    lines: Dict[str, Dict[str, float]] = {}
    demands: Dict[str, float] = {}
    for m in re.finditer(r"产线\s*([0-9A-Za-z]+).*?产能\s*([0-9,.]+).*?成本\s*([0-9,.]+)", problem, re.S):
        cap, cost = _to_number(m.group(2)), _to_number(m.group(3))
        if cap is not None and cost is not None:
            lines[f"Line_{m.group(1)}"] = {"capacity": cap, "cost": cost}
    for m in re.finditer(r"Line\s*([0-9A-Za-z]+).*?capacity\s*(?:=|:|：)?\s*([0-9,.]+).*?cost\s*(?:=|:|：)?\s*([0-9,.]+)", problem, re.I | re.S):
        cap, cost = _to_number(m.group(2)), _to_number(m.group(3))
        if cap is not None and cost is not None:
            lines[f"Line_{m.group(1)}"] = {"capacity": cap, "cost": cost}
    for m in re.finditer(r"([A-Z])\s*(?:产品)?\s*(?:需求|demand)?\s*(?:=|:|：)?\s*([0-9,.]+)", problem):
        val = _to_number(m.group(2))
        if val is not None:
            demands[m.group(1)] = val
    params: Dict[str, Any] = {}
    if lines:
        params["lines"] = lines
    if demands:
        params["demands"] = demands
    return params


def _rule_extract_portfolio(problem: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    budget_match = re.search(r"(?:预算|budget|有)\s*(?:=|:|：)?\s*([0-9,.]+\s*万?)", problem, re.I)
    if budget_match:
        budget = _to_number(budget_match.group(1))
        if budget is not None:
            params["budget"] = budget

    assets: Dict[str, Dict[str, float]] = {}
    for m in re.finditer(r"产品\s*([A-Za-z0-9]+).*?收益\s*([0-9,.]+)\s*%.*?风险(?:等级)?\s*([0-9,.]+)", problem, re.S):
        ret, risk = _to_number(m.group(2)), _to_number(m.group(3))
        if ret is not None and risk is not None:
            assets[f"Asset_{m.group(1)}"] = {"return": ret / 100, "risk": risk}
    if assets:
        params["assets"] = assets
    risk_match = re.search(r"风险(?:等级)?(?:不超过|<=|小于等于|限制|上限)\s*([0-9,.]+)", problem)
    if risk_match:
        risk_limit = _to_number(risk_match.group(1))
        if risk_limit is not None:
            params["risk_limit"] = risk_limit
    return params


def _missing(problem_type: str, params: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for key in REQUIRED_SLOTS.get(problem_type, []):
        value = params.get(key)
        if value in (None, "", [], {}):
            missing.append(key)
    return missing


async def extract_parameters(requirement: RequirementAnalysis) -> ParameterExtractionResult:
    problem_type = requirement.problem_type
    problem = requirement.raw_problem
    params: Dict[str, Any]
    if problem_type == "transportation":
        params = _rule_extract_transportation(problem)
    elif problem_type == "production_planning":
        params = _rule_extract_production(problem)
    elif problem_type == "portfolio":
        params = _rule_extract_portfolio(problem)
    else:
        return ParameterExtractionResult(
            intent=problem_type,
            confidence=0.3,
            extraction_method="unsupported",
            missing_slots=["supported_problem_type"],
            notes=["Only production_planning, transportation and portfolio are currently executable."],
        )

    method = "rule_based"

    # Optional LLM JSON extraction. It fills gaps but cannot generate executable code.
    if settings.use_llm_classification and _missing(problem_type, params):
        prompt = f"""
Extract OR modeling parameters from the user problem as JSON only.
Problem type: {problem_type}
Schema examples:
- transportation: {{"supplies":{{"A":50}}, "demands":{{"X":30}}, "costs":{{"A->X":2}}}}
- production_planning: {{"lines":{{"Line_1":{{"capacity":100,"cost":5}}}}, "demands":{{"A":30}}}}
- portfolio: {{"budget":1000000, "assets":{{"Asset_A":{{"return":0.1,"risk":2}}}}, "risk_limit":2}}
Return only keys that are clearly present. Do not invent values.

User problem:
{problem}
"""
        llm_text = await safe_llm_invoke(prompt, temperature=0.0)
        llm_data = _extract_json(llm_text or "")
        if isinstance(llm_data, dict):
            for key, value in llm_data.items():
                if key not in params or not params[key]:
                    params[key] = value
            method = "rule_based_plus_llm_json"

    missing = _missing(problem_type, params)
    notes: List[str] = []
    if missing:
        notes.append("Some required slots are missing; deterministic template defaults may be used for demo stability.")
    else:
        notes.append("Required slots were extracted into structured parameters.")

    return ParameterExtractionResult(
        intent=problem_type,
        slots=params,
        missing_slots=missing,
        structured_parameters=params,
        confidence=0.85 if not missing else 0.62,
        extraction_method=method,
        notes=notes,
    )


@tool("parameter_extraction_skill")
def parameter_extraction_tool(problem: str) -> str:
    """Extract intent slots and structured OR parameters from a problem statement."""
    # Synchronous tool wrapper for LangChain tool registry demos.
    params = _rule_extract_transportation(problem)
    result = ParameterExtractionResult(
        intent="transportation",
        slots=params,
        structured_parameters=params,
        missing_slots=_missing("transportation", params),
        confidence=0.7,
    )
    return result.model_dump_json(ensure_ascii=False)
