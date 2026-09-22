# Webhooks

Webhooks turn external system events into executable software paths. They should therefore be designed as security-sensitive ingress, not as ordinary HTTP endpoints.

GitHub references:
- validating deliveries: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- webhook best practices: https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks

## Required ingress pipeline

```text
HTTP request
  ↓
TLS / network boundary
  ↓
capture raw body
  ↓
verify signature
  ↓
validate delivery metadata
  ↓
size / replay / event controls
  ↓
schema validation
  ↓
idempotency check
  ↓
enqueue bounded work
  ↓
acknowledge quickly
```

## GitHub signature

GitHub recommends `X-Hub-Signature-256` using HMAC-SHA256 with the webhook secret.

Verification principles:
- calculate HMAC over the original request body
- compare with a constant-time comparison
- never hardcode the secret
- reject missing/invalid signatures before expensive work
- do not alter the body before signature verification

Python example:

```python
import hashlib
import hmac

def verify(raw_body: bytes, secret: bytes, received: str) -> bool:
    expected = "sha256=" + hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)
```

## Replay/idempotency

Webhook delivery may be retried or redelivered. Store a bounded or appropriately retained event identifier and make handlers idempotent.

Do not:
- trigger an irreversible operation directly from the webhook handler
- enqueue unlimited jobs from inbound events
- parse a huge body without a limit
- trust event payload fields without schema validation
- log secrets or complete sensitive payloads unnecessarily

## Backpressure

Webhook handlers should usually:
- verify
- validate
- persist/enqueue bounded work
- respond

Heavy processing belongs outside the request path.

## Language adapters

Implement the same contract in Python, Rust, Go, and TypeScript while keeping the security model constant: raw-body verification first, schema validation second, bounded execution third.