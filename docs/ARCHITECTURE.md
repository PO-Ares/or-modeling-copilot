# Architecture

## Overview

The project uses a **LangChain-based Skills-Agent architecture**. It is designed for local deployment first, with Ollama as the default LLM provider and Qwen/OpenAI-compatible APIs as optional replacements through `.env`.

```text
Browser
  ↓
Streamlit Frontend
  ↓ HTTP
FastAPI Backend
  ↓
Supervisor Agent
  ↓
Skills Layer
  ├── Requirement Analysis Skill
  ├── Production Planning Modeling Skill
  ├── Transportation Modeling Skill
  ├── Portfolio Modeling Skill
  ├── Validation Skill
  ├── Solver Skill
  └── Result Interpretation Skill
  ↓
PuLP/CBC Solver + SQLite Session Metadata
```

## Why skills-agent instead of LangGraph?

The current goal is rapid local/server deployment. LangGraph is powerful for stateful graph orchestration, conditional edges, retries, and human-in-the-loop workflows, but it increases complexity.

This version uses a lighter design:

- LangChain provides the model integration and tool/skill style.
- A Python `SupervisorAgent` coordinates the workflow.
- Each skill has a clear input/output boundary.
- The code is easier to debug and deploy for portfolio demonstration.

## Runtime flow

1. User enters a natural-language OR problem in Streamlit.
2. Streamlit calls FastAPI endpoint `/api/pipeline/full`.
3. Supervisor Agent calls `requirement_analysis_skill`.
4. The requirement skill uses Ollama via LangChain if available; otherwise it falls back to rules.
5. Supervisor selects a modeling skill based on `problem_type`.
6. Validation skill checks generated PuLP model code.
7. Solver skill runs PuLP/CBC and extracts results.
8. Interpretation skill generates a user-friendly explanation.
9. FastAPI returns JSON to Streamlit.
10. Streamlit displays requirement analysis, agent trace, model code, validation, solution, and full JSON.

## Deployment model

### Local default

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
```

### Qwen switch

```env
LLM_PROVIDER=qwen
QWEN_API_KEY=your_real_key
QWEN_MODEL=qwen-plus
```

No code change is required.

## Current limitations

- The current MVP supports three modeling templates.
- LLM is used for classification/requirement extraction, not full arbitrary model generation.
- The generated models are safe fixed templates, which is intentional for deployment stability.
- More OR scenarios should be added as separate skills.

