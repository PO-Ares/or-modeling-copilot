# API Documentation

Base URL:

```text
http://localhost:8000
```

## GET `/api/health`

Returns backend status and runtime architecture.

Example response:

```json
{
  "status": "healthy",
  "message": "Backend is running",
  "version": "0.2.0",
  "architecture": "LangChain-based skills-agent",
  "llm_provider": "ollama",
  "ollama_model": "qwen2.5:1.5b",
  "llm_classification": true
}
```

## POST `/api/pipeline/full`

Runs the full skills-agent workflow.

Request:

```json
{
  "problem_statement": "我有三条产线生产 A/B/C 产品，希望在满足需求的情况下最小化成本。",
  "user_id": "demo_user",
  "session_id": null
}
```

Response fields:

- `session_id`: unique session identifier
- `status`: completed / failed / unsupported
- `architecture`: LangChain-based skills-agent
- `result.requirement_analysis`: problem classification and extracted OR information
- `result.modeling_result`: generated PuLP model
- `result.validation_result`: model validation output
- `result.solve_result`: PuLP/CBC solution
- `result.agent_trace`: visible skills-agent execution trace

## GET `/api/sessions`

Lists recent lightweight session metadata stored in SQLite.

## GET `/api/sessions/{session_id}`

Reads an in-memory session result if the backend has not restarted.

