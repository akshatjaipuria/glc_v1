"""Signal adapter — signal-cli JSON-RPC wire format.

Inbound:  JSON-RPC notification, method "receive".
          params.envelope.source       → sender phone (E.164)
          params.envelope.dataMessage.message → text body
          params.envelope.dataMessage.groupInfo.groupId → group (base64)

Outbound: JSON-RPC request, method "send".
          DM:    params = {recipient, message}
          Group: params = {groupId, message}

Required env vars: SIGNAL_CLI_PATH, SIGNAL_ACCOUNT_NUMBER
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from glc.channels.base import ChannelAdapter
from glc.channels.envelope import ChannelMessage, ChannelReply
from glc.security.trust_level import classify


class Adapter(ChannelAdapter):
    name = "signal"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._rpc_counter = 100

    def _next_rpc_id(self) -> int:
        self._rpc_counter += 1
        return self._rpc_counter

    async def on_message(self, raw: Any) -> ChannelMessage:
        mock = self.config.get("mock")

        # Pop any pending forced-disconnect; surface to operator without raising.
        if mock and mock.pop_disconnect():
            pass  # real impl would close + reopen the socket here

        envelope: dict[str, Any] = raw["params"]["envelope"]

        source: str = envelope.get("source", "")
        source_name: str = envelope.get("sourceName", "")
        timestamp_ms: int = envelope.get("timestamp", 0)
        data_message: dict[str, Any] = envelope.get("dataMessage") or {}

        text: str | None = data_message.get("message")
        group_info: dict[str, Any] = data_message.get("groupInfo") or {}
        group_id: str | None = group_info.get("groupId")

        arrived_at = datetime.fromtimestamp(timestamp_ms / 1000)
        trust = classify("signal", source)

        metadata: dict[str, Any] = {}
        if group_id:
            metadata["signal_group_id"] = group_id

        return ChannelMessage(
            channel="signal",
            channel_user_id=source,
            user_handle=source_name,
            text=text,
            trust_level=trust,
            arrived_at=arrived_at,
            metadata=metadata,
        )

    async def send(self, reply: ChannelReply) -> Any:
        mock = self.config.get("mock")

        params: dict[str, Any] = {"message": reply.text or ""}
        if reply.thread_id:
            # Group reply — address by groupId, never by recipient
            params["groupId"] = reply.thread_id
        else:
            # DM reply
            params["recipient"] = reply.channel_user_id

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_rpc_id(),
            "method": "send",
            "params": params,
        }

        if mock:
            return await mock.send(payload)

        raise RuntimeError(
            "signal-cli not configured — set SIGNAL_CLI_PATH and SIGNAL_ACCOUNT_NUMBER"
        )
