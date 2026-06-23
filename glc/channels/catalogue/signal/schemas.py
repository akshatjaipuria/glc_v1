"""Channel-specific Pydantic types for the signal adapter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SignalGroupInfo(BaseModel, extra="allow"):
    groupId: str
    type: str = "DELIVER"


class SignalDataMessage(BaseModel, extra="allow"):
    message: str | None = None
    timestamp: int = 0
    expiresInSeconds: int = 0
    viewOnce: bool = False
    groupInfo: SignalGroupInfo | None = None


class SignalEnvelope(BaseModel, extra="allow"):
    source: str
    sourceNumber: str | None = None
    sourceName: str = ""
    sourceDevice: int = 1
    timestamp: int = 0
    dataMessage: SignalDataMessage | None = None


class SignalNotification(BaseModel, extra="allow"):
    """JSON-RPC notification from signal-cli `receive` method."""

    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any]
