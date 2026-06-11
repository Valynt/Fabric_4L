import asyncio
import traceback
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    try:
        engine = create_async_engine('postgresql+asyncpg://postgres:postgres@postgres:5432/layer4_agents')
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            print('Raw DB test:', await result.scalar())
        await engine.dispose()
    except Exception as e:
        print('Raw DB test failed:')
        traceback.print_exc()
        return
    
    try:
        import sys
        sys.path.insert(0, '/app')
        sys.path.insert(0, '/app/src')
        from layer4_agents.database import init_db
        await init_db()
        print('init_db succeeded')
    except Exception as e:
        print('init_db failed:')
        traceback.print_exc()

asyncio.run(test())
