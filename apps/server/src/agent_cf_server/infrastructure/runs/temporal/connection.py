"""Bounded connection setup shared by worker and infrastructure checks."""

import asyncio

from temporalio.client import Client


async def connect_temporal(
    address: str, namespace: str, timeout_seconds: float
) -> Client:
    return await asyncio.wait_for(
        Client.connect(address, namespace=namespace), timeout=timeout_seconds
    )
