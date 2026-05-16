# Product Requirements Document

## Product name

Operations Research Modeling Assistant

## Product positioning

A local-deployable AI-assisted modeling assistant that helps users translate business optimization problems into operations research models.

## Target users

- Students learning operations research modeling
- Analysts who need quick LP/MIP prototypes
- Product or operations teams exploring optimization ideas
- Logistics, production, education, and resource allocation scenarios

## Core user pain points

1. Users can describe a business problem but may not know how to formulate it mathematically.
2. OR modeling requires identifying decision variables, objectives, constraints, and solver-compatible code.
3. Traditional modeling has a high learning cost for non-specialists.
4. AI-generated code can be unsafe or unstable if directly executed without constraints.

## MVP scope

The current MVP supports:

- Production planning LP
- Transportation allocation LP
- Portfolio optimization LP
- Requirement classification with local Ollama through LangChain, with rule fallback
- Safe predefined PuLP model templates
- PuLP/CBC solving
- Streamlit interface
- Visible skills-agent execution trace

## Architecture choice

The project uses a **skills-agent architecture** rather than a full LangGraph workflow.

Reason:

- Faster to deploy
- Easier to debug
- Clear modular responsibilities
- Suitable for portfolio demonstration
- Can later evolve into LangChain tool calling or LangGraph orchestration

## User flow

```text
Input problem
  ↓
Requirement Analysis Skill
  ↓
Selected Modeling Skill
  ↓
Validation Skill
  ↓
Solver Skill
  ↓
Interpretation Skill
  ↓
View model, solution, and JSON output
```

## Deployment principle

- GitHub stores only `.env.example`.
- Real `.env` stays on local machine or server.
- Default deployment uses Ollama and does not require cloud API keys.
- Users can switch to Qwen/OpenAI-compatible APIs by changing `.env`.

## Future roadmap

- Add assignment, facility location, scheduling, and simplified VRP skills
- Add password protection and request limits
- Add structured JSON model generation from LLM
- Store full pipeline history and user feedback
- Add report export
- Add Nginx/systemd deployment scripts

