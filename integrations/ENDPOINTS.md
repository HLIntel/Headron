# Endpoint Engineering

An endpoint is a contract plus an operational boundary.

Classes: REST/HTTP, webhook ingress, MCP remote endpoint, health/readiness, metrics, callbacks, internal service, OpenAI-compatible model endpoint.

Document: method, path, auth, schemas, timeout, rate limit, idempotency, pagination, retryability, side effects, observability, versioning.

Request path: `network -> TLS -> auth -> size limit -> parse -> schema validate -> bounded side effect`.

Every retryable side effect needs a defined idempotency model. Agents and bots need explicit pagination budgets.

Separate liveness, readiness, and dependency health.

Keep model endpoint `base_url + model + auth_env + timeout + retry_budget` in provider configuration.
