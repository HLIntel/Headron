# Chat adapter

**Adapter, not a second contract.** Everything a chat needs is generated into [CHAT.md](../../CHAT.md)
from `atlas.yaml/chat`; this page carries only what is specific to a chat session.

## How it loads

Nothing loads by itself, and nothing runs. Paste the install block from `CHAT.md` once into custom
instructions, a project's instructions or a system prompt. From then on the chat routes a file by the
table in `CHAT.md` and fetches one pack's `tools.yaml` by its raw URL.

## What it is routed for

`research` and `ideation`, per `atlas.yaml/model_routes`: quick ideas, primary-source research,
different perspectives, reviews of pasted text, decision records, and a handoff an agent can run.

## The mistake it makes

**Stating a command it never ran as if it passed.** A chat cannot verify. It names the gate that would,
and hands the run to an agent through the `handoff` process.
