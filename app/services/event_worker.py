"""Background asynchronous worker processing durable inbound webhook events."""

import asyncio
import logging

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.database.session import SessionLocal
from app.models.inbound_event import InboundEvent
from app.services.inbound_event_service import InboundEventService

logger = logging.getLogger("aevora.services.event_worker")


class EventWorker:
    """Asynchronous background worker consuming durable inbound events from SQLite."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._is_running = False
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Launch the worker background loop."""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop(), name="whatsapp_event_worker")
        logger.info("WhatsApp durable event background worker started.")

    async def stop(self) -> None:
        """Signal the worker to gracefully shut down."""
        if not self._is_running:
            return
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("WhatsApp durable event background worker stopped.")

    async def _run_loop(self) -> None:
        """Continuous polling loop."""
        interval = self.settings.whatsapp_event_poll_interval_seconds
        while self._is_running:
            try:
                processed_any = await self.process_pending_batch(limit=5)
                if not processed_any:
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Unexpected error in event worker loop: {exc}", exc_info=True)
                await asyncio.sleep(interval)

    async def process_pending_batch(self, limit: int = 5) -> bool:
        """Poll and execute pending events."""
        with SessionLocal() as db:
            stmt = (
                select(InboundEvent.id)
                .where(InboundEvent.status == "pending")
                .order_by(InboundEvent.created_at.asc())
                .limit(limit)
            )
            event_ids = list(db.scalars(stmt).all())

            if not event_ids:
                return False

            for eid in event_ids:
                if not self._is_running:
                    break
                try:
                    await InboundEventService.process_single_event(
                        db=db,
                        event_id=eid,
                        settings=self.settings,
                    )
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    logger.error(f"Error processing event {eid} in worker: {exc}")

            return True


_global_worker: EventWorker | None = None


def get_event_worker() -> EventWorker:
    """Singleton accessor for background event worker."""
    global _global_worker
    if _global_worker is None:
        _global_worker = EventWorker()
    return _global_worker
