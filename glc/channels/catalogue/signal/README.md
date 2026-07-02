# Signal Adapter

Group: Group 13 Signal
Slot: `signal`
Owned path: `glc/channels/catalogue/signal/`

This adapter translates the `signal-cli` JSON-RPC wire format into the
canonical GLC channel envelope and translates `ChannelReply` objects back into
JSON-RPC `send` requests.

## Files

- `adapter.py`: `ChannelAdapter` implementation for inbound receive events and
  outbound replies.
- `schemas.py`: Pydantic v2 models for the `signal-cli` JSON-RPC notification
  and send request shapes.

## Inbound Contract

`signal-cli` receive notifications arrive as JSON-RPC payloads:

```json
{
  "jsonrpc": "2.0",
  "method": "receive",
  "params": {
    "envelope": {
      "source": "+15551234567",
      "sourceName": "Owner",
      "dataMessage": {
        "message": "hello",
        "timestamp": 1710000000000,
        "groupInfo": { "groupId": "base64-group-id" }
      }
    }
  }
}
```

The adapter maps that into `ChannelMessage`:

- `channel`: `signal`
- `channel_user_id`: `params.envelope.source`
- `user_handle`: `sourceName`, falling back to the sender id
- `text`: `dataMessage.message`
- `thread_id`: Signal `groupInfo.groupId` for group messages
- `trust_level`: result of `glc.security.trust_level.classify("signal", sender)`
- `metadata.signal_group_id`: copied group id when present

Non-message events, malformed transport payloads, missing senders, receipt-only
events, and public-channel senders that fail the allowlist check are dropped by
returning `None`. The shared `ChannelAdapter` base currently types
`on_message()` as always returning `ChannelMessage`, so `adapter.py` uses a
narrow `type: ignore[override]` on the Signal override. The runtime behaviour is
intentional and covered by `tests/channels/test_signal.py`.

## Outbound Contract

Direct messages use a Signal recipient:

```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "method": "send",
  "params": {
    "recipient": "+15551234567",
    "message": "hi back"
  }
}
```

Group replies use the Signal group id and must not include a phone recipient:

```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "method": "send",
  "params": {
    "groupId": "base64-group-id",
    "message": "group reply"
  }
}
```

The mock returns rate-limit style failures unchanged so caller policy can decide
whether to retry, defer, or surface the error.

## Trust And Allowlist

The adapter does not invent trust state. It delegates to the shared GLC security
modules:

- `classify("signal", channel_user_id)` assigns `owner_paired`,
  `user_paired`, or `untrusted`.
- `allowed("signal", channel_user_id, ...)` enforces public-channel allowlists
  before a message enters the agent loop.

## Local Verification

Run the Signal-only checks from the repository root:

```bash
uv run pytest tests/channels/test_signal.py -q
uv run ruff check glc/channels/catalogue/signal/
uv run mypy glc/channels/catalogue/signal/
```

The adapter PR workflow also extracts `# Group: Signal` and `# Slot: signal`
from the PR body and checks that changes stay inside this owned path.

## signal-cli Setup Notes

The CI suite uses `tests/channels/mocks/signal_mock.py`; it does not call the
live Signal network. For a live operator demo, run `signal-cli` as a JSON-RPC
daemon with a dedicated bot number and configure:

- `SIGNAL_CLI_PATH`: local path to the `signal-cli` binary.
- `SIGNAL_ACCOUNT_NUMBER`: registered bot phone number.

Signal itself is free, but the bot account needs a registered phone number.
Identity-key safety number changes after reinstall should be handled by the
operator before allowing the account to process trusted messages.
