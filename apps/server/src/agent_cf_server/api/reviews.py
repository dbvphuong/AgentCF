"""API routes for Agent Review decisions and Content Evaluation (AGN-001, AGN-002)."""

from typing import Any, Literal
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.agents.review_repository import ReviewRepository
from agent_cf_server.infrastructure.settings.repository import ResourceNotFoundError


class RecordReviewDecisionRequest(BaseModel):
    attempt_id: str = Field(min_length=1)
    reviewer_agent_id: str = Field(min_length=1)
    revision_round: int = Field(default=1, ge=1)
    decision: Literal["approved", "revision_requested", "escalated"]
    score: float | None = Field(default=None, ge=0.0, le=10.0)
    feedback: str = ""
    violations: list[str] = Field(default_factory=list)
    decision_key: str | None = None


class EvaluateContentRequest(BaseModel):
    content: str
    criteria: dict[str, Any]
    revision_round: int = Field(default=1, ge=1)
    max_revisions: int = Field(default=2, ge=1)


def reviews_router(repository: ReviewRepository) -> APIRouter:
    router = APIRouter(tags=["reviews"])

    @router.post("/v1/task-runs/{task_run_id}/reviews", operation_id="recordReviewDecision", status_code=status.HTTP_201_CREATED)
    def record_decision(
        task_run_id: str,
        payload: RecordReviewDecisionRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        d_key = payload.decision_key or idempotency_key
        try:
            return repository.record_decision(
                task_run_id=task_run_id,
                attempt_id=payload.attempt_id,
                reviewer_agent_id=payload.reviewer_agent_id,
                revision_round=payload.revision_round,
                decision=payload.decision,
                score=payload.score,
                feedback=payload.feedback,
                violations=payload.violations,
                decision_key=d_key,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.get("/v1/task-runs/{task_run_id}/reviews", operation_id="listReviewDecisions")
    def list_decisions(task_run_id: str) -> list[dict[str, Any]]:
        return repository.list_decisions_for_task_run(task_run_id)

    @router.post("/v1/evaluate-content", operation_id="evaluateContent")
    def evaluate_content(payload: EvaluateContentRequest) -> dict[str, Any]:
        return repository.evaluate_content(
            content=payload.content,
            criteria=payload.criteria,
            revision_round=payload.revision_round,
            max_revisions=payload.max_revisions,
        )

    return router
