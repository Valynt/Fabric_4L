import asyncio
import inspect
from layer1_ingestion.shared.tasks import compliance_check_stage
print('asyncio.iscoroutinefunction:', asyncio.iscoroutinefunction(compliance_check_stage))
print('inspect.iscoroutinefunction:', inspect.iscoroutinefunction(compliance_check_stage))
