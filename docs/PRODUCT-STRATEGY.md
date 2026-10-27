# Product Strategy

**Repository contract: v3.60.0**

This document records Thea's product architecture, pricing model, and deployment strategy. It defines the boundary between the public MIT-licensed core and the private commercial companion runtime.

## Product identity

Thea is an AI engineering workspace and orchestration system with independent verification built in. Verification is the foundation, but the product serves broader needs: managing agents, organizing context, working with files, controlling tool permissions, maintaining project rules, and moving work between chat and coding environments.

## Five product benefits

**Workspace**

One place to see projects, active agents, tasks, files, verification results, and recent activity.

**Orchestration**

Mind selects the appropriate agent or tool, organizes work, manages task transitions, and prepares recovery or handoff steps. Users keep their preferred AI providers.

**Context and files**

Connect project folders, inspect files, retrieve relevant context, and carry project knowledge between sessions without repeatedly loading everything into a model.

**Chat and integrations**

Use Thea through chat, MCP, CLI, IDEs, or the graphical workspace. A conversation can prepare work for an agent, and an agent can return a structured result.

**Contracts and proof**

Rules define what agents may do and what evidence they owe. Thea verifies execution results and records what is complete, failed, or unverified.

## Repository structure

| Repository | License | Content |
|---|---|---|
| HLIntel/TheaSoftware | Public · MIT | Core verification, basic Mind, CLI, public contracts, receipt format, read-only MCP, integrations, SDK |
| TheaOS | Private · Commercial | Workspace UI, advanced orchestration, paid agent workflows, context management, collaboration, account integration, team governance |
| Thea Web | Hosted frontend | Browser interface, sign-in, license entitlements, secure connection to the customer's local host |

The private TheaOS repository contains the desktop and web frontend. The public repository supplies a stable engine that both consume.

## Public vs Private boundary

| Capability | Public MIT Core | Private TheaOS |
|---|---|---|
| Deterministic verification | Full | Uses Core |
| Receipt format and integrity checks | Full | Adds workflow management |
| Basic Mind classification and routing | Full | Advanced orchestration |
| CLI and read-only MCP | Full | Permissioned execution controls |
| Language and tool contracts | Full | Visual contract management |
| Agent adapters | Full | Multi-agent workspace |
| Basic context intake | Full | Persistent context workflows |
| Chat skill and handoff format | Full | Integrated chat workspace |
| File search and routing | Full | Interactive file workspace |
| Storage format and adapters | Full | Native agent storage handoff |
| Personal rules | Full basic support | Advanced rule editor |
| Team policies and approvals | — | Paid |
| Account and subscription integration | — | Paid |

The boundary is **protocol versus experience**. Keep the receipt format, contract specification, and verification semantics public. Sell the interface, advanced coordination, collaboration, and managed policy workflows built around that standard.

## Pricing model

Three tiers: Free, Pro, and Team. No per-token billing, no separate Mind-call or receipt subscriptions.

### What makes the plans worth paying for

Free gets users comfortable with Thea's verification foundation and integrations.

Pro sells a better everyday experience: one interface, multiple agents, useful context, better workflows, fewer repeated instructions, and more control over execution.

Team sells coordination and authority: shared policies, permissions, approval flows, handoffs, and visibility across users and agents.

### Unlimited engine

| Capability | Policy |
|---|---|
| Local Core checks | Unlimited |
| Local Mind operations within licensed features | Unlimited |
| Receipt creation | Unlimited |
| Local file interactions | Unlimited within user permissions |
| Agent sessions | Unlimited |
| Local MCP calls | Unlimited |
| BYOS storage | No Thea volume cap |
| Agent-provider tokens | Paid to the user's provider, not Thea |

Thea has sensible CPU, memory, concurrency, and security controls, but no artificial internal usage ceilings.

## Storage architecture

Receipt and context storage follows a native-agent-first approach.

| Destination | Type | Description |
|---|---|---|
| Native agent storage | Preferred | The connected agent stores its own context, files, and receipt references |
| Project folder | Direct filesystem | Local drive, user-controlled files |
| Obsidian | Vault as ordinary files | User-owned vault |
| Drive / Dropbox | Synced local directories | Synced folders, not direct API |

Thea facilitates and verifies: write request → storage reference → read-back → hash comparison.

Avoid direct Google Drive and Dropbox APIs initially. Synced folders cover desktop use cases with less maintenance. For context, maintain small indexes and references rather than copying complete chat histories or project folders.

## Deployment architecture

Deploy the graphical frontend to Vercel, but keep execution and sensitive project access in a local Thea host.

### TheaOS Web — Vercel

Interface, account, subscription, workspace navigation. Browser-to-local connection via explicit pairing, authenticated requests, and scoped permissions.

### Thea Local Host

Core, Mind, agents, files, MCP, receipts. Runs in the user's environment with access to repositories, agent providers, local tools, and own storage.

### Deployment verdict

| Approach | Verdict |
|---|---|
| Entire dashboard on localhost | Keep as fallback |
| Entire product on Vercel | Not recommended — cannot execute against local files |
| Vercel frontend + local host | **Best target** — accessible UI with local execution |
| Hosted remote execution | Later, if demand exists |

For the first release, use browser-to-local communication on the same machine, not a publicly exposed local API. Support remote-device access later through an authenticated outbound tunnel.

## Login and data separation

| Lives on Vercel / auth service | Lives with the user |
|---|---|
| Account identity | Repository files |
| Subscription entitlement | Agent credentials |
| License activation | Conversation content |
| Basic device registration | Context indexes |
| Frontend application | Receipts and contracts |
| Minimal pairing metadata | Verification and execution |

Do not put agent API keys, repository contents, or raw receipts into Vercel environment variables or application databases.

### User journey

1. Visit TheaOS in the browser and sign in.
2. Install or launch Thea Local Host.
3. Pair the browser with the local host using a short-lived authorization flow.
4. Choose a project folder and connect existing agents.
5. Use chat, file exploration, orchestration, verification, and receipts from one interface.

When the local host is offline, the interface loads and shows that local execution and files are unavailable.

## Build stages

**Stage 1 — One usable workspace**

Connect the existing dashboard to the local host. Make projects, agents, files, context, and receipts usable together. Keep local access working without an account.

The local host API server exposes Thea's core functionality via FastAPI endpoints for verification, routing, gating, project info, doctor checks, commands, search, and intake.

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Server health and version info |
| `/verify` | POST | Run verification gates (unlimited for Free) |
| `/route` | POST | Route a file to language and gates |
| `/gate` | POST | Run a specific gate for a file |
| `/project/info` | GET | Get project information and detected languages |
| `/doctor` | GET | Check toolchain availability |
| `/check` | POST | Run full contract check |
| `/commands` | GET | List available Thea commands |
| `/find` | POST | Search the atlas index |
| `/intake` | POST | Digest user prompt into a task |

The server is started via the `thea-host` command, available when the `host` optional dependency group is installed.

**Stage 2 — Web frontend**

Extract the UI into a deployable frontend and host it on Vercel. Add secure local pairing and connection status. Avoid moving the execution engine into serverless functions.

**Stage 3 — Everyday AI workflows**

Add chat-to-task handoffs, file-aware context, agent switching, task history, and native storage. This is where Pro becomes valuable beyond verification.

**Stage 4 — Paid accounts and teams**

Add entitlements, shared policies, approvals, and collaboration. Charge for higher-level workflows, not individual local executions.

## Migration from MIT to paid product

### Phase 1 — Establish the boundary

Keep the public repository and its history intact. Create the private commercial repository separately. Define which APIs and contract formats are shared.

Do not make the existing public repository private. Public forks remain public after a visibility change.

### Phase 2 — Package Core as a dependency

The private product consumes versioned public Core releases, not a copied version of the verification engine. Pin the Core version and test compatibility automatically.

### Phase 3 — Move commercial interfaces

Place the TheaOS frontend, commercial host controls, advanced agent workflows, and collaboration features in the private product. Move only code with the right to relicense.

### Phase 4 — Migrate customer state

Introduce a versioned export/import format for rules, project connections, context references, and receipt indexes. Leave actual project files and receipts in user-owned storage.

### Phase 5 — Activate paid collaboration

Introduce Pro entitlements and Team workspaces only after personal workflows work reliably. A Free user upgrading to Pro unlocks capabilities without reinstalling Core or moving receipts.

## Migration safeguards

Before splitting the code:

1. Public CLI and MCP compatibility remain intact.
2. Private modules do not accidentally enter public build artifacts.
3. Public CI does not depend on private repositories or secrets.
4. Private packages retain required third-party license notices.
5. Existing receipts remain readable across versions.
6. Free users can continue using MIT Core without an account.
7. The private frontend cannot grant permissions that the local host has not authorized.

## OpenSSF Scorecard improvements

The public repository follows OpenSSF Scorecard best practices to build trust with the
community and signal security maturity.

### Completed

- **SLSA provenance** — Every release is attested with `actions/attest-build-provenance`,
  cryptographically binding artifacts to the build workflow.
- **SBOM generation** — Each release includes an SPDX-formatted Software Bill of Materials
  generated by `anchore/sbom-action`.
- **Dependabot** — Automated dependency updates for github-actions, pip, and gomod ecosystems.
- **Fuzzing** — Nightly fuzzing tests run via `fuzz-nightly.yml` workflow.
- **Security policy** — `SECURITY.md` defines vulnerability reporting and response process.

### Requires manual admin action

- **Branch protection** — Enable the `main-protection` ruleset enforcement via GitHub Settings.
- **Vulnerability alerts** — Enable via GitHub Settings → Code security.
- **Code review requirements** — Update ruleset to require 1 approving review.
- **CII Best Practices** — Enroll at bestpractices.coreinfrastructure.org.

See `docs/SCORECARD-IMPROVEMENT.md` for the full audit and step-by-step instructions.

## Long-term value

Build two mutually reinforcing assets:

**Public standard:** Thea's verification contracts, receipt format, language support, and integrations become familiar to developers and AI-agent platforms.

**Commercial product:** TheaOS becomes the preferred environment for coordinating agents, managing context, working with files, applying rules, and proving completion across teams.

This model leaves room for future enterprise licensing, private deployments, and OEM partnerships without hosting customer data.
