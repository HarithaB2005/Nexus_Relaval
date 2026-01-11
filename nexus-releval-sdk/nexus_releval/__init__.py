"""
Nexus Releval SDK - 5-Minute Integration
Official Python SDK for the Nexus Releval AI Auditor API

Quick Start:
    import nexus_releval
    client = nexus_releval.Client(api_key="your_key")
    result = client.verify("Your prompt here...")
"""

__version__ = "1.0.0"

from .client import Client, NexusClient

__all__ = ["Client", "NexusClient"]

