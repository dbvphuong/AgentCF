"""A durable no-side-effect check, not the production Process interpreter."""

from temporalio import workflow


@workflow.defn(name="AgentCFFoundationPersistenceProbeV1")
class FoundationPersistenceProbe:
    def __init__(self) -> None:
        self._marker = ""
        self._finish_requested = False

    @workflow.run
    async def run(self, marker: str) -> dict[str, str | bool]:
        self._marker = marker
        await workflow.wait_condition(lambda: self._finish_requested)
        return {"marker": self._marker, "completed": True}

    @workflow.query
    def snapshot(self) -> dict[str, str | bool]:
        return {"marker": self._marker, "finish_requested": self._finish_requested}

    @workflow.signal
    def finish(self) -> None:
        # Replaying or repeating the signal has no external side effect.
        self._finish_requested = True
