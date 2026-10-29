---
title: WebSocket
description: The /ws/status live-update protocol and client examples.
---

`/ws/status` is a broadcast WebSocket for live job updates. It has no
authentication and no subscription model. Every connected client receives every
message.

## Connecting

```text
ws://<host>/ws/status
wss://<host>/ws/status   (behind TLS)
```

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/status');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  switch (msg.cmd) {
    case 'reload':
      refetchJobs();
      break;
    case 'status':
      updateJobStatus(msg.uid, msg.status);
      break;
    case 'output':
      appendOutput(msg.uid, msg.line);
      break;
  }
};
```

The server accepts the connection and then loops on `receive_text()`. It does not
send pings and does not require an initial message. Keep the socket open. If the
client closes it, the server removes it from the broadcast list.

## Messages

### `reload`

Sent whenever the queued/running/finished job set changes, for example when a job
is queued, starts, finishes, or is removed.

```json
{"cmd":"reload"}
```

Clients must refetch `GET /jobs`.

### `status`

Sent when a job calls `PUT /job/{uid}/status`.

```json
{
  "cmd": "status",
  "uid": "e3b0c44298fc1c149afbf4c8996fb924",
  "status": {
    "status": "working",
    "total": 123,
    "passed": 80,
    "failed": 2,
    "eta": "00:12:31"
  }
}
```

The `status` object is the same free-form object the job sent. Any extra
top-level fields included in the PUT body are also present in the message.

### `output`

Sent once per output line while a task runs.

```json
{
  "cmd": "output",
  "uid": "e3b0c44298fc1c149afbf4c8996fb924",
  "line": "-- building tests/sys/shell\n"
}
```

Carriage returns in the process output are replaced with `\n`.

## Reconnection

The server does not replay missed messages. A reconnecting client must:

1. refetch `GET /jobs`,
2. refetch the active job's `output_text_url` (or `GET /job/{uid}`),
3. continue appending WebSocket output.

## Example: `websocat`

```sh
websocat ws://localhost:8000/ws/status
```

## Example: Python

```python
import asyncio, json
import websockets

async def main():
    async with websockets.connect("ws://localhost:8000/ws/status") as ws:
        async for raw in ws:
            print(json.loads(raw))

asyncio.run(main())
```
