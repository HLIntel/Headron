# Google Antigravity adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to Antigravity: how the atlas is loaded
here, and the skill it discovers.

## How it loads

Antigravity reads `AGENTS.md`, `GEMINI.md`, `.agents/rules/`, and `.agents/skills/`. The Headron
skill is at [`.agents/skills/headron/SKILL.md`](../../.agents/skills/headron/SKILL.md): one folder
per skill, with a `SKILL.md` that carries `name` and `description` frontmatter. The Gemini
configuration directory [`.gemini/`](../../.gemini/HEADRON.md) points to that skill and holds no
second copy of it.

Keep every rule file thin and let it point at `AGENTS.md`: a second copy of the rules is the drift
this repository refuses.

## Use its strength

Antigravity takes long context and visual review well. Give it the route, not the whole tree:

```bash
python scripts/atlas.py port <file|dir> --frame agent --json
python scripts/atlas.py find "<query>" --snippet
```

Run the contract before claiming done:

```bash
python scripts/atlas.py check && python scripts/verify.py
```

## Native tools stay

Antigravity keeps every tool it ships with — file, shell, search, edit, browser, and agent tools —
configured in its own settings, and it may add, replace or drop any of them without asking
Headron. Headron is added to this layer, never swapped in for it: its shell runs the `headron` /
`python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP
client may mount the read-only Headron route beside whatever servers it already has. An install
writes only the git hook and never edits this runtime's tool configuration
(`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract
narrows commands only inside a run that opted into one.

## The mistake it makes

**A visual or long-context pass that replaces the gates.** A review that reads the whole change and
says it looks right has not run the route. Name the gates from `port`, then run them and read the
exit code.
