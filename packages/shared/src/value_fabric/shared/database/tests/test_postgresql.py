import pytest

from value_fabric.shared.database.postgresql import session_scope, transactional


class FakeSession:
    def __init__(self, state):
        self.state = state

    async def commit(self):
        self.state["committed"] += 1

    async def rollback(self):
        self.state["rolled_back"] += 1


class SessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSessionMaker:
    def __init__(self, state):
        self.state = state

    def __call__(self):
        if self.state.get("exhaust"):
            if self.state.get("opened", 0) >= 1:
                raise RuntimeError("pool exhausted")
            self.state["opened"] = 1
        return SessionCtx(FakeSession(self.state))


@pytest.mark.asyncio
async def test_connection_exhaustion_behavior() -> None:
    state = {"committed": 0, "rolled_back": 0, "exhaust": True}
    maker = FakeSessionMaker(state)

    async with session_scope(maker):
        pass

    with pytest.raises(RuntimeError, match="pool exhausted"):
        async with session_scope(maker):
            pass


@pytest.mark.asyncio
async def test_stale_connection_style_reuse() -> None:
    state = {"committed": 0, "rolled_back": 0}
    maker = FakeSessionMaker(state)

    async with session_scope(maker):
        pass
    async with session_scope(maker):
        pass

    assert state["committed"] == 2


@pytest.mark.asyncio
async def test_failed_transaction_rolls_back() -> None:
    state = {"committed": 0, "rolled_back": 0}
    maker = FakeSessionMaker(state)

    async def boom(_session):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await transactional(maker, boom)

    assert state["rolled_back"] == 1
