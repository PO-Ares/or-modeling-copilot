"""Streamlit frontend for the Operations Research Modeling Assistant.

Geek-style UI with a large banner image, light/dark switching, and a clean
left-navigation + main-content layout. The frontend keeps only features that are
actually implemented by the FastAPI backend.
"""

from __future__ import annotations

import base64
import json
import os
import time
from html import escape
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import requests
import streamlit as st

# -----------------------------------------------------------------------------
# Page configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="运筹优化建模助手",
    page_icon="∑",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
ASSET_DIR = Path(__file__).parent / "assets"
BACKGROUND_PATH = ASSET_DIR / "or_background.png"

EXAMPLES = {
    "生产计划优化": """我是一个工厂的计划经理。我们有3条产线，可以生产A、B、C三种产品。
- 产线1每月产能1000单位，成本100元/单位
- 产线2每月产能800单位，成本120元/单位
- 产线3每月产能600单位，成本150元/单位

需求是A产品500单位，B产品400单位，C产品300单位。
问怎么分配生产才能最小化成本？""",
    "配送分配优化": """我们有3个配送中心，需要给10个客户配送商品。
- 配送中心1库存200件，运费每公里10元
- 配送中心2库存150件，运费每公里12元
- 配送中心3库存180件，运费每公里8元

每个客户的需求量为10-30件不等，平均距离为50公里。
问如何分配配送任务才能最小化总成本？""",
    "投资组合优化": """我有100万元需要投资，有4种投资产品：
- 产品A：年化收益10%，风险等级2
- 产品B：年化收益8%，风险等级1
- 产品C：年化收益12%，风险等级3
- 产品D：年化收益6%，风险等级1

目标是最大化收益，同时限制平均风险等级不超过2。
问应该如何分配投资？""",
}

TEMPLATE_DESCRIPTIONS = {
    "生产计划优化": "产能、需求与单位成本约束下的生产分配。",
    "配送分配优化": "配送中心到客户区域的运输成本最小化。",
    "投资组合优化": "预算和风险限制下的收益最大化。",
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def image_to_base64(path: Path) -> str:
    """Read a local image and return a base64 data URI."""
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def check_backend() -> bool:
    """Check whether the FastAPI backend is reachable."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def call_full_pipeline(problem_statement: str) -> Dict[str, Any]:
    """Call the full modeling pipeline."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/pipeline/full",
            json={"problem_statement": problem_statement},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc)}


def apply_theme(theme: str) -> None:
    """Apply CSS variables and layout styles."""
    is_dark = theme == "深色"
    bg_uri = image_to_base64(BACKGROUND_PATH)

    if is_dark:
        palette = {
            "page": "#07111f",
            "page2": "#0b1730",
            "panel": "rgba(12, 25, 46, 0.92)",
            "panel2": "rgba(16, 33, 58, 0.86)",
            "text": "#eaf6ff",
            "muted": "#9ab0c8",
            "border": "rgba(94, 234, 212, 0.20)",
            "accent": "#22d3ee",
            "accent2": "#60a5fa",
            "green": "#34d399",
            "warn": "#fbbf24",
            "shadow": "0 22px 60px rgba(0, 0, 0, 0.34)",
            "sidebar": "#0a1425",
            "code": "#07111f",
        }
    else:
        palette = {
            "page": "#eef6fb",
            "page2": "#f8fbff",
            "panel": "rgba(255, 255, 255, 0.92)",
            "panel2": "rgba(245, 250, 255, 0.96)",
            "text": "#112235",
            "muted": "#5b6b7e",
            "border": "rgba(37, 99, 235, 0.13)",
            "accent": "#0077b6",
            "accent2": "#2dd4bf",
            "green": "#059669",
            "warn": "#d97706",
            "shadow": "0 22px 55px rgba(30, 64, 175, 0.12)",
            "sidebar": "#f5f9fd",
            "code": "#f8fafc",
        }

    hero_bg = (
        f"linear-gradient(90deg, rgba(3, 10, 24, 0.68), rgba(8, 28, 55, 0.30)), url('{bg_uri}')"
        if bg_uri else
        "linear-gradient(120deg, rgba(7, 29, 53, 0.98), rgba(0, 119, 182, 0.62))"
    )

    st.markdown(
        f"""
<style>
    :root {{
        --page: {palette['page']};
        --page2: {palette['page2']};
        --panel: {palette['panel']};
        --panel2: {palette['panel2']};
        --text: {palette['text']};
        --muted: {palette['muted']};
        --border: {palette['border']};
        --accent: {palette['accent']};
        --accent2: {palette['accent2']};
        --green: {palette['green']};
        --warn: {palette['warn']};
        --shadow: {palette['shadow']};
        --sidebar: {palette['sidebar']};
        --code: {palette['code']};
    }}

    #MainMenu, footer, header {{visibility: hidden;}}
    [data-testid="stToolbar"] {{display: none;}}

    html, body, [class*="css"] {{
        font-family: "Inter", "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
    }}

    .stApp {{
        background:
            radial-gradient(circle at 15% 12%, rgba(45, 212, 191, 0.12), transparent 28%),
            radial-gradient(circle at 90% 4%, rgba(0, 119, 182, 0.13), transparent 32%),
            linear-gradient(135deg, var(--page), var(--page2));
        color: var(--text);
    }}

    .block-container {{
        max-width: 1500px;
        padding-top: 1.1rem;
        padding-bottom: 2.5rem;
    }}

    section[data-testid="stSidebar"] {{
        background: var(--sidebar);
        border-right: 1px solid var(--border);
    }}

    section[data-testid="stSidebar"] * {{
        color: var(--text) !important;
    }}

    h1, h2, h3, h4, h5, h6, p, label, span {{
        color: var(--text);
    }}

    .top-hero {{
        min-height: 310px;
        border-radius: 0 0 30px 30px;
        overflow: hidden;
        margin: -1.1rem 0 24px 0;
        padding: 42px 48px;
        display: flex;
        align-items: flex-end;
        background-image: {hero_bg};
        background-size: cover;
        background-position: center;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
    }}

    .hero-content {{
        max-width: 760px;
    }}

    .hero-eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.13);
        border: 1px solid rgba(255, 255, 255, 0.22);
        color: #dff7ff;
        font-size: 0.9rem;
        margin-bottom: 14px;
        backdrop-filter: blur(10px);
    }}

    .hero-title {{
        color: white !important;
        font-size: 3.1rem;
        line-height: 1.05;
        letter-spacing: -0.055em;
        font-weight: 920;
        margin-bottom: 12px;
        text-shadow: 0 6px 26px rgba(0, 0, 0, 0.34);
    }}

    .hero-subtitle {{
        color: rgba(235, 250, 255, 0.92) !important;
        font-size: 1.08rem;
        max-width: 760px;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.28);
    }}

    .layout-grid {{
        display: grid;
        grid-template-columns: 310px minmax(0, 1fr);
        gap: 22px;
        align-items: start;
    }}

    .side-panel, .panel, .metric-card, .template-box, .flow-box {{
        border: 1px solid var(--border);
        background: var(--panel);
        border-radius: 22px;
        box-shadow: var(--shadow);
    }}

    .side-panel {{
        padding: 18px;
        position: sticky;
        top: 20px;
    }}

    .panel {{
        padding: 24px;
        margin-bottom: 18px;
    }}

    .panel-title {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 860;
        font-size: 1.25rem;
        margin-bottom: 7px;
    }}

    .panel-subtitle {{
        color: var(--muted);
        font-size: 0.95rem;
        margin-bottom: 16px;
    }}

    .brand-line {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
    }}

    .logo-box {{
        width: 44px;
        height: 44px;
        display: grid;
        place-items: center;
        border-radius: 15px;
        background: linear-gradient(135deg, var(--accent), var(--accent2));
        color: white !important;
        font-weight: 900;
        font-size: 1.35rem;
        box-shadow: 0 14px 30px rgba(0, 119, 182, 0.24);
    }}

    .brand-name {{
        font-weight: 900;
        font-size: 1.35rem;
        letter-spacing: -0.04em;
    }}

    .muted {{ color: var(--muted) !important; }}

    .model-chip {{
        border: 1px solid var(--border);
        background: var(--panel2);
        border-radius: 16px;
        padding: 12px 14px;
        margin: 14px 0;
    }}

    .model-chip .label {{
        font-size: 0.82rem;
        color: var(--muted) !important;
        margin-bottom: 5px;
    }}

    .model-chip .value {{
        font-weight: 800;
    }}

    .template-box {{
        box-shadow: none;
        background: var(--panel2);
        padding: 13px 14px;
        margin-bottom: 10px;
    }}

    .template-title {{
        font-weight: 850;
        margin-bottom: 4px;
    }}

    .template-desc {{
        color: var(--muted) !important;
        font-size: 0.88rem;
    }}

    .flow-grid {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-top: 10px;
    }}

    .flow-box {{
        background: var(--panel2);
        box-shadow: none;
        padding: 14px;
        text-align: center;
    }}

    .flow-icon {{
        width: 40px;
        height: 40px;
        display: grid;
        place-items: center;
        margin: 0 auto 8px auto;
        border-radius: 13px;
        background: linear-gradient(135deg, rgba(0,119,182,0.13), rgba(45,212,191,0.16));
        border: 1px solid var(--border);
        font-size: 1.2rem;
    }}

    .flow-name {{
        font-weight: 820;
        font-size: 0.9rem;
    }}

    .metric-grid {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 13px;
        margin-bottom: 18px;
    }}

    .metric-card {{
        background: var(--panel2);
        box-shadow: none;
        padding: 15px 16px;
    }}

    .metric-label {{
        color: var(--muted) !important;
        font-size: 0.82rem;
        margin-bottom: 7px;
    }}

    .metric-value {{
        color: var(--text) !important;
        font-size: 1rem;
        font-weight: 850;
        overflow-wrap: anywhere;
    }}

    .result-card {{
        border: 1px solid var(--border);
        background: linear-gradient(180deg, var(--panel), var(--panel2));
        border-radius: 22px;
        padding: 20px 22px;
        box-shadow: var(--shadow);
        margin-bottom: 16px;
    }}

    .card-header {{ display: flex; align-items: center; gap: 12px; font-weight: 900; font-size: 1.15rem; margin-bottom: 10px; }}
    .card-icon {{ width: 36px; height: 36px; display: grid; place-items: center; border-radius: 13px; background: linear-gradient(135deg, var(--accent), var(--accent2)); color: white !important; box-shadow: 0 12px 24px rgba(0,119,182,0.18); }}
    .soft-note {{ border-radius: 18px; padding: 16px 18px; background: rgba(45, 212, 191, 0.10); border: 1px solid rgba(45, 212, 191, 0.22); margin: 12px 0; }}
    .warning-note {{ border-radius: 18px; padding: 16px 18px; background: rgba(251, 191, 36, 0.13); border: 1px solid rgba(251, 191, 36, 0.28); margin: 12px 0; }}
    .timeline {{ position: relative; margin: 10px 0 0 0; padding-left: 28px; }}
    .timeline::before {{ content: ""; position: absolute; left: 10px; top: 8px; bottom: 8px; width: 2px; background: linear-gradient(var(--accent), var(--accent2)); opacity: 0.55; }}
    .timeline-item {{ position: relative; padding: 0 0 24px 18px; }}
    .timeline-dot {{ position: absolute; left: -26px; top: 2px; width: 22px; height: 22px; display: grid; place-items: center; border-radius: 999px; background: linear-gradient(135deg, var(--accent), var(--accent2)); color: white; font-size: 0.75rem; font-weight: 900; box-shadow: 0 8px 20px rgba(0,119,182,0.25); }}
    .timeline-title {{ font-weight: 900; margin-bottom: 6px; }}
    .timeline-status {{ display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: 999px; font-size: 0.76rem; font-weight: 800; background: rgba(52, 211, 153, 0.14); color: var(--green) !important; border: 1px solid rgba(52, 211, 153, 0.22); }}
    .timeline-summary {{ color: var(--muted) !important; line-height: 1.7; }}
    .data-table {{ width: 100%; border-collapse: separate; border-spacing: 0; overflow: hidden; border-radius: 18px; border: 1px solid var(--border); background: var(--panel2); }}
    .data-table th, .data-table td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); text-align: left; }}
    .data-table th {{ color: var(--muted) !important; font-size: 0.86rem; background: rgba(0,119,182,0.06); }}
    .data-table tr:last-child td {{ border-bottom: none; }}


    div[data-testid="stTextArea"] textarea {{
        border-radius: 18px;
        border: 1px solid var(--border);
        background: var(--panel2);
        color: var(--text);
        min-height: 245px;
        font-size: 0.98rem;
    }}

    div[data-testid="stTextArea"] textarea:focus {{
        border-color: var(--accent);
        box-shadow: 0 0 0 1px var(--accent);
    }}

    .stButton button {{
        border-radius: 14px;
        border: 1px solid var(--border);
        background: var(--panel2);
        color: var(--text);
        font-weight: 780;
        min-height: 43px;
    }}

    .stButton button[kind="primary"] {{
        border: none;
        background: linear-gradient(135deg, var(--accent), var(--accent2));
        color: white;
        box-shadow: 0 14px 28px rgba(0, 119, 182, 0.22);
    }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 13px;
        padding: 10px 14px;
        background: var(--panel2);
        border: 1px solid var(--border);
    }}

    div[data-testid="stCodeBlock"] {{
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid var(--border);
        background: var(--code);
    }}

    @media (max-width: 1120px) {{
        .layout-grid {{ grid-template-columns: 1fr; }}
        .side-panel {{ position: static; }}
        .flow-grid, .metric-grid {{ grid-template-columns: repeat(2, 1fr); }}
        .top-hero {{ min-height: 250px; padding: 32px 28px; }}
        .hero-title {{ font-size: 2.3rem; }}
    }}
</style>
""",
        unsafe_allow_html=True,
    )


def render_flow_panel(label: str, progress: int = 0) -> None:
    """Render a visible modeling flow and progress bar."""
    st.markdown(
        """
<div class="panel">
    <div class="panel-title">建模流程</div>
    <div class="panel-subtitle">{label}</div>
    <div class="flow-grid">
        <div class="flow-box"><div class="flow-icon">⌁</div><div class="flow-name">需求分析</div></div>
        <div class="flow-box"><div class="flow-icon">∑</div><div class="flow-name">模型构建</div></div>
        <div class="flow-box"><div class="flow-icon">✓</div><div class="flow-name">模型验证</div></div>
        <div class="flow-box"><div class="flow-icon">⚙</div><div class="flow-name">优化求解</div></div>
        <div class="flow-box"><div class="flow-icon">↗</div><div class="flow-name">结果解释</div></div>
    </div>
</div>
""".format(label=label),
        unsafe_allow_html=True,
    )
    st.progress(progress)

# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "problem_input" not in st.session_state:
    st.session_state.problem_input = ""
if "result" not in st.session_state:
    st.session_state.result = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "theme" not in st.session_state:
    st.session_state.theme = "浅色"

# -----------------------------------------------------------------------------
# Theme + top banner
# -----------------------------------------------------------------------------
with st.sidebar:
    st.session_state.theme = st.radio(
        "界面模式",
        ["浅色", "深色"],
        horizontal=True,
        index=0 if st.session_state.theme == "浅色" else 1,
    )

apply_theme(st.session_state.theme)

st.markdown(
    """
<div class="top-hero">
    <div class="hero-content">
        <div class="hero-eyebrow">Operations Research · Optimization Modeling</div>
        <div class="hero-title">运筹优化建模助手</div>
        <div class="hero-subtitle">输入生产、配送或投资场景中的优化问题，系统将完成建模流程并返回可运行的优化模型与求解结果。</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Main layout
# -----------------------------------------------------------------------------
side_col, main_col = st.columns([0.30, 0.70], gap="large")

with side_col:
    st.markdown(
        f"""
<div class="side-panel">
    <div class="brand-line">
        <div class="logo-box">∑</div>
        <div>
            <div class="brand-name">OR Assistant</div>
            <div class="muted">运筹优化建模助手</div>
        </div>
    </div>
    <div class="model-chip">
        <div class="label">当前模型</div>
        <div class="value">{LLM_PROVIDER} · {OLLAMA_MODEL}</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("#### 示例模板")
    for name, description in TEMPLATE_DESCRIPTIONS.items():
        st.markdown(f"**{name}**")
        st.caption(description)
        if st.button(f"使用{name}", key=f"use_{name}", use_container_width=True):
            st.session_state.problem_input = EXAMPLES[name]
            st.session_state.result = None
            st.rerun()
        st.write("")

with main_col:
    st.markdown(
        """
<div class="panel">
    <div class="panel-title">问题描述</div>
    <div class="panel-subtitle">请尽量说明目标、变量、约束条件和关键参数。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    problem = st.text_area(
        "问题描述",
        key="problem_input",
        label_visibility="collapsed",
        placeholder="例如：我有3条产线，需要生产3种产品，希望在满足需求和产能的情况下最小化总成本。",
    )

    b1, b2 = st.columns([1.5, 1])
    with b1:
        run_clicked = st.button("开始建模", type="primary", use_container_width=True)
    with b2:
        reset_clicked = st.button("重置", use_container_width=True)

    if reset_clicked:
        st.session_state.problem_input = ""
        st.session_state.result = None
        st.session_state.processing = False
        st.rerun()

    if run_clicked:
        if not problem.strip():
            st.error("请输入问题描述。")
        elif not check_backend():
            st.error("后端未连接，请先运行 python main.py。")
        else:
            st.session_state.processing = True
            st.session_state.result = None
            st.rerun()

    if st.session_state.processing and st.session_state.problem_input.strip():
        render_flow_panel("正在执行建模流程。", 15)
        time.sleep(0.25)
        with st.spinner("正在计算，请稍等..."):
            result = call_full_pipeline(st.session_state.problem_input)
        if "error" in result:
            st.session_state.processing = False
            st.error(f"建模失败：{result['error']}")
        else:
            render_flow_panel("建模流程完成。", 100)
            time.sleep(0.25)
            st.session_state.result = result
            st.session_state.processing = False
            st.rerun()

    if not st.session_state.result:
        render_flow_panel("等待输入问题。", 0)


def display_name(value: str) -> str:
    """Convert internal technical labels into user-facing Chinese labels."""
    mapping = {
        "production_planning": "生产计划优化",
        "transportation": "运输分配优化",
        "portfolio": "投资组合优化",
        "unsupported": "暂不支持的问题类型",
        "rule_based": "规则解析",
        "rule_based_plus_llm_json": "规则解析 + 大模型结构化补全",
        "llm_json": "大模型结构化抽取",
        "none": "无",
        "Optimal": "最优",
        "Infeasible": "不可行",
        "Unbounded": "无界",
        "failed": "求解失败",
        "generated": "已生成",
        "completed": "完成",
        "passed": "通过",
        "needs_revision": "需修改",
        "partial": "待补充",
    }
    return mapping.get(str(value), str(value))


def missing_name(value: str) -> str:
    mapping = {
        "lines": "产线/产能与成本信息",
        "demands": "需求信息",
        "costs": "运输成本表",
        "supplies": "供应量信息",
        "budget": "投资预算",
        "assets": "投资产品信息",
        "risk_limit": "风险上限",
    }
    return mapping.get(str(value), str(value))


def render_card(title: str, icon: str, body_html: str) -> None:
    st.markdown(
        f'''
<div class="result-card">
  <div class="card-header"><div class="card-icon">{escape(icon)}</div><div>{escape(title)}</div></div>
  <div>{body_html}</div>
</div>
''',
        unsafe_allow_html=True,
    )


def render_kv_table(rows: list[tuple[str, str]]) -> None:
    html = '<table class="data-table"><thead><tr><th>字段</th><th>内容</th></tr></thead><tbody>'
    for k, v in rows:
        html += f'<tr><td>{escape(str(k))}</td><td>{escape(str(v))}</td></tr>'
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


def render_solution_table(solution: Dict[str, Any]) -> None:
    html = '<table class="data-table"><thead><tr><th>变量</th><th>取值</th></tr></thead><tbody>'
    for k, v in solution.items():
        if v is None:
            continue
        try:
            val = f"{float(v):.2f}"
        except Exception:
            val = str(v)
        name = str(k).replace("produce_", "生产 ").replace("ship_", "运输 ").replace("amount_", "投资 ")
        name = name.replace("_", " ").replace("'", "").replace("(", "").replace(")", "")
        html += f'<tr><td>{escape(name)}</td><td>{escape(val)}</td></tr>'
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------------
if st.session_state.result:
    result = st.session_state.result
    payload = result.get("result", {})
    req = payload.get("requirement_analysis", {}) or {}
    model = payload.get("modeling_result", {}) or {}
    validation = payload.get("validation_result", {}) or {}
    solve = payload.get("solve_result", {}) or {}
    trace = payload.get("agent_trace", []) or []

    problem_type = display_name(req.get("problem_type", req.get("display_name", "-")))
    objective = req.get("objective", "-")
    var_count = len(req.get("decision_variables", []) or [])
    con_count = len(req.get("constraints", []) or [])
    status = display_name(solve.get("status", "-"))

    st.markdown(
        f'''
<div class="panel">
    <div class="panel-title">结果概览</div>
    <div class="panel-subtitle">系统已完成从自然语言问题到优化模型的结构化处理。</div>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">问题类型</div><div class="metric-value">{escape(problem_type)}</div></div>
        <div class="metric-card"><div class="metric-label">优化目标</div><div class="metric-value">{escape(str(objective))}</div></div>
        <div class="metric-card"><div class="metric-label">决策变量</div><div class="metric-value">{var_count}</div></div>
        <div class="metric-card"><div class="metric-label">约束条件</div><div class="metric-value">{con_count}</div></div>
        <div class="metric-card"><div class="metric-label">求解状态</div><div class="metric-value">{escape(status)}</div></div>
    </div>
</div>
''',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["需求分析", "流程轨迹", "模型代码", "验证结果", "最优解", "完整 JSON"])

    with tabs[0]:
        render_card(
            "需求识别结果",
            "🔎",
            f"<p><b>识别问题类型：</b>{escape(problem_type)}</p>"
            f"<p><b>目标函数：</b>{escape(str(objective))}</p>"
            f"<p><b>参数抽取方式：</b>{escape(display_name(req.get('extraction_method', '-')))}</p>",
        )
        if req.get("structured_parameters"):
            render_card("关键参数", "🧩", "<p>系统已将输入问题转换为结构化参数，供后续建模与求解使用。</p>")
            st.json(req.get("structured_parameters"))
        if req.get("decision_variables"):
            st.markdown("#### 决策变量")
            for item in req.get("decision_variables", []) or []:
                st.write(f"- {item}")
        if req.get("constraints"):
            st.markdown("#### 约束条件")
            for item in req.get("constraints", []) or []:
                st.write(f"- {item}")
        if req.get("missing_slots"):
            st.markdown('<div class="warning-note"><b>需要补充的信息：</b></div>', unsafe_allow_html=True)
            for item in req.get("missing_slots", []):
                st.write(f"- {missing_name(item)}")
        else:
            # Clarification prompts are only shown when the system truly needs more input.
            # After a successful structured extraction and solve, stale prompts are hidden.
            stale_words = ["运输成本", "成本表", "供应", "需求", "请提供"]
            suggestions = []
            for item in req.get("clarifications_needed", []) or []:
                text = str(item)
                if any(word in text for word in stale_words):
                    continue
                suggestions.append(text)
            if suggestions and req.get("problem_type") == "unsupported":
                st.markdown('<div class="soft-note"><b>进一步补充信息：</b></div>', unsafe_allow_html=True)
                for item in suggestions:
                    st.write(f"- {item}")

    with tabs[1]:
        if trace:
            html = '<div class="timeline">'
            for item in trace:
                step = escape(str(item.get('step', '')))
                skill = escape(str(item.get('skill', '')))
                stat = escape(display_name(item.get('status', '')))
                summary = escape(str(item.get('summary', '')))
                html += f'''
<div class="timeline-item">
  <div class="timeline-dot">{step}</div>
  <div class="timeline-title">{skill}<span class="timeline-status">{stat}</span></div>
  <div class="timeline-summary">{summary}</div>
</div>
'''
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("暂无流程轨迹。")

    with tabs[2]:
        render_card("优化模型", "∑", f"<p>{escape(model.get('model_description', '暂无模型描述。'))}</p>")
        st.code(model.get("model_code", "# No model code generated"), language="python")

    with tabs[3]:
        if validation.get("is_valid"):
            st.success("模型验证通过")
        else:
            st.error("模型需要补充或修改")
        if validation.get("issues"):
            st.markdown("#### 发现的问题")
            for issue in validation["issues"]:
                st.write(f"- {issue}")
        if validation.get("suggestions"):
            st.markdown("#### 改进建议")
            for suggestion in validation["suggestions"]:
                st.write(f"- {suggestion}")
        render_kv_table([("模型状态", "可执行" if validation.get("is_valid") else "需要补充或修改")])

    with tabs[4]:
        render_kv_table([("求解状态", status)])
        if solve.get("objective_value") is not None:
            st.metric("最优目标值", f"{solve['objective_value']:.2f}")
        if solve.get("solution"):
            st.markdown("#### 最优方案")
            render_solution_table(solve.get("solution"))
        if solve.get("explanation"):
            st.info(solve.get("explanation"))
        if solve.get("sensitivity_analysis"):
            st.markdown("#### 求解说明")
            st.json(solve.get("sensitivity_analysis"))

    with tabs[5]:
        st.json(result)
        st.download_button(
            "下载 JSON 报告",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name=f"modeling_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
