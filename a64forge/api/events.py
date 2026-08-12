from __future__ import annotations

import asyncio

from a64forge.schemas import ProgressEvent


class EventBroker:
    def __init__(self) -> None:
        self.subscribers: set[asyncio.Queue[ProgressEvent]] = set()

    async def publish(self, event: ProgressEvent) -> None:
        for queue in tuple(self.subscribers):
            await queue.put(event)

    def subscribe(self) -> asyncio.Queue[ProgressEvent]:
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue(maxsize=200)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[ProgressEvent]) -> None:
        self.subscribers.discard(queue)


broker = EventBroker()

