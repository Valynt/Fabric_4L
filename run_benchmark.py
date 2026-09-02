import asyncio
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path("services/layer4-agents/src").resolve()))
from layer4_agents.services.pack_variable_loader import PackVariableLoader

class MockRegistry:
    async def get_variable(self, id): return None
    async def register_variable(self, var):
        await asyncio.sleep(0)

async def background_task(stop_event):
    max_delay = 0
    last = time.perf_counter()
    while not stop_event.is_set():
        await asyncio.sleep(0.001)
        now = time.perf_counter()
        delay = (now - last) - 0.001
        if delay > max_delay:
            max_delay = delay
        last = now
    return max_delay

def _sync_read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

async def main():
    registry = MockRegistry()
    p = Path("/tmp/benchmark_packs")
    p.mkdir(exist_ok=True)

    pack_dir = p / "huge_pack"
    pack_dir.mkdir(exist_ok=True)

    vars_list = [
        {
            "variable_id": f"var_{i}",
            "canonicalName": f"Var {i}",
            "description": f"Description {i} " * 10,
            "type": "string"
        }
        for i in range(100000)
    ]
    with open(pack_dir / "variables.json", "w") as f:
        json.dump({"variables": vars_list}, f)

    loader = PackVariableLoader(registry=registry, packs_dir=p)

    import importlib
    importlib.invalidate_caches()

    stop_event = asyncio.Event()
    bg = asyncio.create_task(background_task(stop_event))

    start = time.perf_counter()
    await loader.load_pack("huge_pack")
    total_time = time.perf_counter() - start

    stop_event.set()
    max_delay = await bg

    print(f"Total time: {total_time:.4f}s")
    print(f"Max event loop delay (blocking): {max_delay:.4f}s")

if __name__ == "__main__":
    asyncio.run(main())
