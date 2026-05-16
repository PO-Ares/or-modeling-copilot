"""Shared schemas for the skills-agent runtime."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RequirementAnalysis(BaseModel):
    """Structured understanding of the user's OR problem."""

    problem_type: str = Field(..., description="Internal problem type, e.g. production_planning")
    display_name: str = Field(..., description="Human-readable problem name")
    decision_variables: List[str]
    objective: str
    constraints: List[str]
    clarifications_needed: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    llm_used: bool = False
    raw_problem: str = ""

    # Added in v0.3: intent + slot filling + structured parameter extraction.
    intent: str = ""
    slots: Dict[str, Any] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    structured_parameters: Dict[str, Any] = Field(default_factory=dict)
    extraction_method: str = "none"


class ParameterExtractionResult(BaseModel):
    """Intent, slots, and normalized parameters extracted from natural language."""

    intent: str
    slots: Dict[str, Any] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    structured_parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    extraction_method: str = "rule_based"
    notes: List[str] = Field(default_factory=list)


class ModelingResult(BaseModel):
    """Generated optimization model."""

    model_description: str
    model_code: str
    status: str = "generated"
    skill_used: str


class ValidationResult(BaseModel):
    """Validation output for generated model code."""

    is_valid: bool
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    skill_used: str = "validation_skill"


class SolveResult(BaseModel):
    """Optimization solver output."""

    status: str
    objective_value: Optional[float] = None
    solution: Dict[str, Any] = Field(default_factory=dict)
    explanation: Optional[str] = None
    sensitivity_analysis: Dict[str, Any] = Field(default_factory=dict)
    skill_used: str = "solver_skill"


class AgentTraceStep(BaseModel):
    """One visible trace step in the skills-agent workflow."""

    step: str
    skill: str
    status: str
    summary: str


class PipelineResult(BaseModel):
    """Complete skills-agent pipeline result."""

    requirement_analysis: RequirementAnalysis
    modeling_result: ModelingResult
    validation_result: ValidationResult
    solve_result: SolveResult
    agent_trace: List[AgentTraceStep]
    architecture: str = "LangChain-based skills-agent"
