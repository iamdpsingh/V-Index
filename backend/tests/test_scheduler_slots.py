import asyncio

from vindex import worker


def test_slow_fetch_does_not_hold_an_entire_batch_and_cancellation_drains(monkeypatch):
    async def check():
        started = []
        finished = set()
        cancelled = set()
        release_slow = asyncio.Event()
        all_fast_done = asyncio.Event()

        def due(limit, active_ids):
            return [i for i in range(1, 5) if i not in active_ids and i not in finished][:limit]

        async def refresh(source_id, **kwargs):
            started.append(source_id)
            try:
                if source_id == 1:
                    await release_slow.wait()
                finished.add(source_id)
                if {2, 3, 4}.issubset(finished):
                    all_fast_done.set()
            except asyncio.CancelledError:
                cancelled.add(source_id)
                raise

        monkeypatch.setattr(worker, "due_source_ids", due)
        monkeypatch.setattr(worker, "refresh", refresh)
        task = asyncio.create_task(worker.schedule(2))
        await asyncio.wait_for(all_fast_done.wait(), timeout=2)
        assert started == [1, 2, 3, 4] and 1 not in finished
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert cancelled == {1}

    asyncio.run(check())
