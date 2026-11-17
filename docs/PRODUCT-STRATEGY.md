# Product boundary and package architecture

**Repository contract: v3.64.0**

Headron is an open-source verification foundation for AI-assisted engineering. It provides local verification, contracts, receipts, agent integrations, and a read-only MCP interface. The local core does not require an account.

Headron Harness is a separate workspace and runtime that can consume the public core. Mind API is a separate hosted service intended to provide verification planning to supported clients. Planned capabilities are not evidence that a service or integration is available; consult the [public site](https://headron.tech/) for current product information.

## Open-core boundary

The platform separates open-source engine capabilities from private hosted and enterprise infrastructure:

| Capability | Open source (MIT, `HLIntel/Headron`) | Private / Hosted (`HLIntel`, `HeadronLayer`) |
|---|---|---|
| Core verification engine | Deterministic gates, invariants, and local verifier | None |
| Evidence & receipts | Tamper-evident receipts and signature validators | Cross-repository audit retention |
| Agent connectivity | Local MCP server, CLI, and client protocol schemas | Hosted Mind planning and quota metering |
| GitHub integration | GitHub Action and GitHub App integration layer | Hosted webhook worker, private keys, and installation token vault |
| Coordination & UI | None (headless and non-interactive) | Headron Harness (multi-repo workspace and approvals) |

Rule of thumb: anything that runs on the user's machine or defines an open format is open source. Anything that requires a long-lived secret, billing, tenant isolation, or managed infrastructure is private.

## The five capability packages

The platform organizes capabilities into five distinct modules:

1. **Headron Core (`headron-core`):** Deterministic verification engine, contract evaluator, change-class gating, and mutation defense.
2. **Headron Harness (`headron-harness`):** Agent coordination workspace, execution telemetry, human-in-the-loop approvals, and multi-repo orchestration.
3. **Headron Mind (`headron-mind`):** Contextual intelligence, graph planning, risk projection, and execution optimization.
4. **Headron Proof (`headron-proof`):** Tamper-evident execution receipts, cryptographic proof chaining, and policy certificates.
5. **Headron Connect (`headron-connect`):** Unified gateway across MCP, CLI, REST API, GitHub Apps, and OAuth.

## The five-step loop

Engineering workflows follow a deterministic loop:

1. **Task:** analyze change intent, class, and affected paths.
2. **Contract:** resolve obligations, required gates, and invariants.
3. **Execution:** run hermetic checks non-interactively.
4. **Proof:** record exact statuses (`PASS`, `FAIL`, `NOT RUN`, `REUSED`).
5. **Receipt:** seal immutable evidence bound to the source tree.

## Keyless onboarding architecture

To eliminate onboarding friction, users connect through scoped, revocable authorization rather than manual API key pasting:

- **Interactive agents and IDEs:** OAuth 2.1 with PKCE generates short-lived session tokens. Agent tools receive no raw secret parameters.
- **GitHub repositories:** GitHub App single-click installation mints scoped, short-lived installation tokens for pull request checks.
- **Headless CLI:** browser single sign-on or device authorization flow establishes authenticated sessions.
- **Automated CI/CD:** scoped API keys remain available for unattended services and external pipelines.
- **Public discovery:** anonymous read-only MCP queries explore documentation and catalog routes without authentication.

## Data and integration boundary

Public contracts and client integrations should remain usable independently of private services. Local project files, agent credentials, and receipts remain under the user's control. Account identity, subscriptions, and service entitlement belong to their respective hosted services.

A hosted service must describe the data it receives and its handling before customers rely on it. Checkout, key issuance, and entitlement enforcement require end-to-end verification before their behavior can be assumed.

Private product code and operations must not be required to run the public core or its verification. Shared formats and compatibility should be tested across their owning implementations.
