from __future__ import annotations

"""Integration clients for Layer 4 to communicate with other layers.

Provides hybrid integration approach where L4 agents orchestrate
L1 (Ingestion), L2 (Extraction), and L3 (Knowledge Graph) via API calls.
"""


from .layer1_client import Layer1IngestionClient
from .layer2_client import Layer2ExtractionClient
from .layer3_client import Layer3Client, Layer3ClientError

__all__ = [
    "Layer1IngestionClient",
    "Layer2ExtractionClient",
    "Layer3Client",
    "Layer3ClientError",
]
