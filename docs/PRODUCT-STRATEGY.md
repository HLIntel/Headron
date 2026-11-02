# Product Strategy

**Repository contract: v3.61.0**

This document records product direction and proposals, not a statement that each capability has shipped. It defines the intended boundary between the public MIT-licensed verifier and companion products.

## Product identity

Headron is the public verification foundation for AI-assisted engineering. A broader workspace and orchestration experience is a product direction, with capabilities to be proven in their owning products before they are described as available.

## Five product benefits

**Workspace**

One place to see projects, active agents, tasks, files, verification results, and recent activity.

**Orchestration**

Mind selects the appropriate agent or tool, organizes work, manages task transitions, and prepares recovery or handoff steps. Users keep their preferred AI providers.

**Context and files**

Connect project folders, inspect files, retrieve relevant context, and carry project knowledge between sessions without repeatedly loading everything into a model.

**Chat and integrations**

Use Headron through chat, MCP, CLI, IDEs, or the graphical workspace. A conversation can prepare work for an agent, and an agent can return a structured result.

**Contracts and proof**

Rules define what agents may do and what evidence they owe. Headron verifies execution results and records what is complete, failed, or unverified.

## Repository structure

| Repository      | License              | Content                                                                                                                             |
| --------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| HLIntel/Headron | Public · MIT         | Core verification, basic Mind, CLI, public contracts, receipt format, read-only MCP, integrations, SDK                              |
| HeadronOS       | Private · Commercial | Workspace UI, advanced orchestration, paid agent workflows, context management, collaboration, account integration, team governance |
| Headron Web     | Hosted frontend      | Public site and account sign-in; paid key checkout is in development                                                                |

The private HeadronOS repository contains the desktop and web frontend. The public repository supplies a stable engine that both consume.

## Public vs Private boundary

| Capability                            | Public MIT Core    | Private HeadronOS               |
| ------------------------------------- | ------------------ | ------------------------------- |
| Deterministic verification            | Full               | Uses Core                       |
| Receipt format and integrity checks   | Full               | Adds workflow management        |
| Basic Mind classification and routing | Full               | Advanced orchestration          |
| CLI and read-only MCP                 | Full               | Permissioned execution controls |
| Language and tool contracts           | Full               | Visual contract management      |
| Agent adapters                        | Full               | Multi-agent workspace           |
| Basic context intake                  | Full               | Persistent context workflows    |
| Chat skill and handoff format         | Full               | Integrated chat workspace       |
| File search and routing               | Full               | Interactive file workspace      |
| Storage format and adapters           | Full               | Native agent storage handoff    |
| Personal rules                        | Full basic support | Advanced rule editor            |
| Team policies and approvals           | —                  | Paid                            |
| Account and subscription integration  | —                  | Paid                            |

The boundary is **protocol versus commercial service**. Keep the receipt format, contract specification, verification semantics, and client integrations public. Keep credentials, customer data, billing, entitlement decisions, and private product operations in their owning private services.

## Open-core commercial architecture

Headron uses an open-core architecture to balance bottom-up developer adoption with defensible commercial monetization and enterprise acquisition value.

The proposed product has two complementary layers:

1. **Open core (Free · MIT)**: A genuinely useful, unhobbled local developer foundation:
   - CLI verification engine and gate enforcement
   - Local deterministic checks and failure pattern detection
   - Machine-readable receipt format and cryptographic verification
   - Read-only stdio MCP server for connected coding assistants
   - Language and tool contracts

2. **Commercial surface (planned)**: A paid Mind API key and MCP integration for compatible agents, chats, and other clients. Advanced workspaces, shared execution, and team capabilities are possible future products, not included with the Mind API key.

This separation protects commercial upside and defensibility without degrading the local developer experience.

## Pricing model

The [public plans](https://headron.tech/#plans) describe product direction. [Account & Access](https://headron.tech/checkout.html) supports account sign-in; paid checkout and commercial key provisioning are not yet available.

### What makes the plans worth paying for

Free gives individual developers the complete local verification foundation and integrations without an account or key.

Mind API is intended to provide a paid key for supported API and MCP integrations across agent, chat, cloud, and customer-hosted environments. Its purchase, key issuance, and entitlement enforcement must be verified before launch.

Pro is a proposed HeadronOS workspace for coordinating agents, approvals, and verification.

Team capabilities such as shared rules and collaboration are proposals.

Enterprise deployment and support options are proposals.

### Intended usage policy

| Capability                                     | Policy                                   |
| ---------------------------------------------- | ---------------------------------------- |
| Local Core checks                              | Unlimited                                |
| Local Mind operations within licensed features | Unlimited                                |
| Receipt creation                               | Unlimited                                |
| Local file interactions                        | Unlimited within user permissions        |
| Agent sessions                                 | Unlimited                                |
| Local MCP calls                                | Unlimited                                |
| BYOS storage                                   | No Headron volume cap                    |
| Agent-provider tokens                          | Paid to the user's provider, not Headron |

These are product targets, not evidence of a deployed service or an entitlement policy. Resource and security controls still apply; published paid plans are not yet available.

## Storage architecture

Receipt and context storage follows a native-agent-first approach.

| Destination          | Type                     | Description                                                               |
| -------------------- | ------------------------ | ------------------------------------------------------------------------- |
| Native agent storage | Preferred                | The connected agent stores its own context, files, and receipt references |
| Project folder       | Direct filesystem        | Local drive, user-controlled files                                        |
| Obsidian             | Vault as ordinary files  | User-owned vault                                                          |
| Drive / Dropbox      | Synced local directories | Synced folders, not direct API                                            |

Headron facilitates and verifies: write request → storage reference → read-back → hash comparison.

Avoid direct Google Drive and Dropbox APIs initially. Synced folders cover desktop use cases with less maintenance. For context, maintain small indexes and references rather than copying complete chat histories or project folders.

## Deployment architecture

The paid key and MCP integration form the intended Mind service boundary. Compatible clients can run in an agent, chat, cloud, or customer-controlled environment. Execution, storage, and access to project data remain with the user's chosen environment; a shared execution platform is a possible future product.

## Login and data separation

| Account and billing service | Lives with the user          |
| --------------------------- | ---------------------------- |
| Account identity            | Repository files             |
| Subscription entitlement    | Agent credentials            |
| License activation          | Conversation content         |
| Basic device registration   | Context indexes              |
| Frontend application        | Local receipts and contracts |
| Minimal pairing metadata    | Verification and execution   |

Do not send agent API keys or repository contents to the hosted service. A shared handoff or receipt requires an explicit user-approved submission; its storage, access, and deletion must be explained before synchronization is enabled.

The proposed paid journey is to sign in, subscribe, create a key, and configure a supported API or MCP client. Purchase and key issuance are not yet available.

## Build stages

**Stage 1 — One usable workspace**

Connect the existing dashboard to the local host. Make projects, agents, files, context, and receipts usable together. Keep local access working without an account.

A local host connection is planned. Its API, permissions, packaging and end-to-end behavior must be verified in the implementation before they are presented as available.

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

Place the HeadronOS frontend, commercial host controls, advanced agent workflows, and collaboration features in the private product. Move only code with the right to relicense.

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

## Long-term value

Build two mutually reinforcing assets:

**Public standard:** Headron's verification contracts, receipt format, language support, and integrations become familiar to developers and AI-agent platforms.

**Commercial product:** HeadronOS becomes the preferred environment for coordinating agents, managing context, working with files, applying rules, and proving completion across teams.

This model leaves room for future enterprise licensing, private deployments, and OEM partnerships without hosting customer data.
