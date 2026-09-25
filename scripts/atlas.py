"""Atlas router + repository contract.

Design (0.9.7): atlas.yaml is the single source of truth. Every roster below is
read from it, every document section that restates it is generated from it, and
every count the contract resolves is printed, so a clean pass is always legible.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess

import yaml
from agentpolicy import (
    action_command,
    action_errors,
    agent_policy_errors,
    authority_class_errors,
    claim_errors,
    command_verdict,
    gate_command,
    gate_tool_errors,
    process_errors,
    process_record,
    required_gates,
    runner_errors,
)
from atlascore import (
    BLOB_SUFFIXES,
    CHANGE_CLASSES,
    CODE_SUFFIXES,
    EXEMPT,
    HTML_LINK_RE,
    LINK_RE,
    MAX_BLOB_BYTES,
    MAX_CODE_LINES,
    ORPHAN_ROOTS,
    PRECEDENCE_IMPLEMENTED,
    REQUIRED_WIKI,
    ROOT,
    VERSION_SITES,
    atlas,
    known_labels,
    label_for,
    link_target,
    read,
    read_jsonc,
    rel,
    route_for,
    route_targets,
    route_with_evidence,
    routes,
    tracked,
)
from contextcost import (
    entry_cost_errors,
    example_coverage_errors,
    footprint_errors,
    generated_attribute_errors,
    mechanism_doc_errors,
    tighten_ratchets,
    wheel_import_errors,
)
from doctor import main as doctor_main
from identity import identity_errors
from knowledge import knowledge_errors, pick, why
from packmanifest import manifest_errors


# THE SELF-MAINTENANCE MODULES ARE IMPORTED LAZILY, AND THAT IS A PACKAGING DECISION, NOT A STYLE
# ONE. atlasgen generates THIS repository's documents and atlasinv checks THIS repository's 26
# invariants; a consumer routing a file in their own tree needs neither, and shipping 55 KB of them
# in the wheel made every consumer carry the maintenance of a repository they do not have. They are
# declared development-only, so they exist in a checkout and not in an install — which is exactly
# why the import has to be inside the function that needs it. `contextcost.wheel_import_errors()`
# refuses a module-level import of either, because that failure is invisible from a checkout and
# appears only for the consumer, at import time.
def _selfcheck():
    """The generator and the invariant roster, together, for the commands that maintain this tree."""
    import atlasgen
    import atlasinv
    return atlasgen, atlasinv


def declaration_errors() -> tuple[list[str], list[str]]:
    """What this repository DECLARES about itself: the dependency lock against its range, the
    instrument roster against scripts/, and the router's precedence against atlas.yaml.

    EXTRACTED BECAUSE THE RATCHET FIRED, and that is the whole point of having one.
    `astshape.py` reported check() at 281 lines against a cap of 278 — a cap set to the
    measured worst three edits earlier. Raising a cap to fit the code it was measuring is how a
    ratchet becomes a record of whatever happened last, so the function was split instead.
    """
    errors: list[str] = []
    warnings: list[str] = []
    # A LOCK IS DERIVED, SO IT MUST BE CHECKED AGAINST WHAT IT WAS DERIVED FROM. A lock that pins
    # a version outside the declared range is a second declaration, and the copy that installs is
    # the one that decides.
    lock_text = read("scripts/requirements.lock.txt")
    pinned = re.search(r"^([A-Za-z0-9._-]+)==([0-9][^\s\\]*)", lock_text, re.M)
    if not pinned:
        errors.append("scripts/requirements.lock.txt pins nothing with ==")
    elif "--hash=sha256:" not in lock_text:
        errors.append("scripts/requirements.lock.txt carries no hashes, so --require-hashes is a no-op")
    else:
        # NOT `version`: that name already holds the CONTRACT version in this function, and
        # shadowing it made `check` print "contract 6.0.3" — the dependency's version, in the line
        # that tells a reader which contract just passed.
        name, lock_version = pinned.group(1).lower(), pinned.group(2)
        ranged = read("scripts/requirements.txt")
        floor = re.search(rf"{name}>=([0-9][^,\s]*)", ranged, re.I)
        ceiling = re.search(rf"{name}[^,]*,<([0-9][^\s]*)", ranged, re.I)
        def parts(text: str) -> tuple[int, ...]:
            return tuple(int(p) for p in re.findall(r"\d+", text))
        if not floor or not ceiling:
            errors.append(f"scripts/requirements.txt does not declare a range for {name}")
        elif not parts(floor.group(1)) <= parts(lock_version) < parts(ceiling.group(1)):
            errors.append(f"lock pins {name}=={lock_version}, outside the declared range in "
                          f"scripts/requirements.txt (>={floor.group(1)},<{ceiling.group(1)})")
        if f'"{name}>=' not in read("pyproject.toml").lower():
            warnings.append(f"pyproject.toml does not mirror the {name} range")

    # A WHEEL THAT SILENTLY GAINS OR LOSES A MODULE. py-modules is an enumerated roster, which is
    # the shape this repository distrusts everywhere else — so it is asserted against scripts/*.py
    # in both directions. A module in the tree and not in the wheel is a command that works here
    # and fails for a consumer; a module in the wheel and not in the tree fails the build.
    packaged = set(re.findall(r'"([a-z_][a-z0-9_]*)"', re.search(
        r"py-modules = \[(.*?)\]", read("pyproject.toml"), re.S).group(1)))
    on_disk = {p.stem for p in (ROOT / "scripts").glob("*.py")}
    dev_only = {str(n) for n in ((atlas().get("context_policy") or {})
                                 .get("install_footprint") or {}).get("development_only") or []}
    for name in sorted(on_disk - packaged - dev_only):
        errors.append(f"scripts/{name}.py is in neither pyproject py-modules nor "
                      "install_footprint/development_only — it would work from a checkout and be "
                      "missing from an install, or ship to consumers who never asked for it")
    for name in sorted((packaged | dev_only) - on_disk):
        errors.append(f"'{name}' is declared shipped or development-only, and scripts/ has no such file")
    for name in sorted(packaged & dev_only):
        errors.append(f"'{name}' is declared both shipped and development-only")

    declared_precedence = [str(p) for p in (atlas().get("routing_policy") or {}).get("precedence") or []]
    for rule in PRECEDENCE_IMPLEMENTED:
        if rule not in declared_precedence:
            errors.append(f"router implements precedence '{rule}', absent from atlas.yaml/routing_policy")
    return errors, warnings


def tracked_file_errors() -> tuple[list[str], list[str]]:
    """Per-file checks over the tracked tree: secrets, oversized code, oversized blobs.

    Extracted when `astshape.py` reported check() over its line cap for the second time. The
    cap falls with each split; raising it to fit the function it measures would make the
    ratchet a record of whatever happened last.
    """
    errors: list[str] = []
    warnings: list[str] = []
    for path in tracked():
        if path.name.startswith(".env") and path.name != ".env.example":
            errors.append(f"tracked environment/secret file: {rel(path)}")
        suffix = path.suffix.lower()
        if suffix in CODE_SUFFIXES and path.is_file():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    line_count = sum(1 for _ in handle)
                if line_count > MAX_CODE_LINES:
                    warnings.append(f"large code file: {rel(path)} ({line_count} lines > {MAX_CODE_LINES})")
            except (OSError, UnicodeDecodeError) as exc:
                warnings.append(f"unreadable code file: {rel(path)} ({exc.__class__.__name__})")
        if suffix in BLOB_SUFFIXES and path.is_file():
            size = path.stat().st_size
            if size > MAX_BLOB_BYTES:
                warnings.append(f"large binary/blob artifact: {rel(path)} ({size} bytes > {MAX_BLOB_BYTES})")
    return errors, warnings


def cross_reference_errors() -> list[str]:
    """Rosters that point at each other, checked BOTH WAYS.

    Every one of these was one-directional: the contract proved a route had a label, and never that
    a label had a route. The reverse direction is what catches something added through a UI or left
    behind by a deletion — a label for a language that no longer routes, a gate named by the build
    order that no policy declares, two instruments claiming one file.
    """
    errors: list[str] = []
    data = atlas()

    # 1. LABELS, BOTH WAYS. A lang/* label with no route is debris; a route with no label already
    #    failed. Namespaces come from the declaration, so a label outside them is unfiled.
    catalog = known_labels()
    routed = {label_for(target) for target in route_targets()}
    prefixes = tuple(str(p) for p in ((data.get("routing_policy") or {}).get("issue_labels") or {}).values())
    for label in sorted(catalog):
        if label.startswith("lang/") and label not in routed:
            errors.append(f"label '{label}' is in the catalog and no route resolves to it")
        if prefixes and not label.startswith(prefixes):
            errors.append(f"label '{label}' is outside every declared namespace prefix")

    # 2. THE BUILD ORDER NAMES GATE CLASSES; each must be one the policy declares.
    gates = set((data.get("verification_policy") or {}).get("profiles") or {})
    for step in data.get("build_order") or []:
        gate = str((step or {}).get("gate"))
        if gate not in gates:
            errors.append(f"build_order step '{(step or {}).get('step')}' names gate '{gate}', "
                          "which verification_policy does not declare")

    # 3. ONE FILE, ONE INSTRUMENT. Two entries claiming one script means one of them is unowned.
    claimed: dict[str, str] = {}
    for name, spec in (data.get("instruments") or {}).items():
        script = str((spec or {}).get("script"))
        if script in claimed:
            errors.append(f"instruments '{name}' and '{claimed[script]}' both claim {script}")
        claimed[script] = name

    # 4. EVERY EXAMPLE RUNNER NAMES A REAL ROUTE, so a recipe cannot sit unreachable.
    for route in (data.get("example_runners") or {}):
        if route not in route_targets():
            errors.append(f"example_runners declares a recipe for '{route}', which is not a route")

    # 5. TASK PROFILES AND TOOL PROFILES cross-reference: a tool profile named by no task is dead
    #    weight, and `polyglot` composing `core-code` must find it.
    tool_profiles = data.get("tool_profiles") or {}
    for name, entries in tool_profiles.items():
        for entry in entries or []:
            if str(entry) in tool_profiles and str(entry) == name:
                errors.append(f"tool_profile '{name}' composes itself")
    return errors


def required_path_errors() -> list[str]:
    """Every path this repository must contain, and every alias symlink that must resolve.

    Extracted when the structure gate refused check() for the third time. The cap has fallen
    278 -> 262 -> 259 -> here; each step is a function the gate refused and a split that earned
    the lower number.
    """
    errors: list[str] = []
    required = [
        "MODEL.md", "README.md", "VERSION", "atlas.yaml", "docs/INDEX.md", "docs/LANGUAGE-SPEC.md",
        "docs/GITHUB-FINALIZATION.md", "languages/ATLAS.md", "models/README.md", "models/vscode/README.md",
        "integrations/VS-CODE.md", "integrations/MCP-LANGUAGE-MATRIX.md", "integrations/MCP-PROFILES.md",
        "systems/POLYGLOT-ENGINEERING.md", "systems/AGENT-HARNESS.md", "patterns/ANTI-DRIFT.md",
        "patterns/ANTI-ORPHANS.md", "patterns/ANTI-MUTATION.md", "patterns/BOUNDARY-BREAKAGE.md",
        "patterns/ANTI-BLOBS.md", ".github/copilot-instructions.md", ".github/dependabot.yml",
        ".github/workflows/dependency-review.yml", ".github/workflows/scorecard.yml",
        ".github/pull_request_template.md", ".github/CODEOWNERS", "SECURITY.md", "config/github-labels.json",
        ".editorconfig", ".gitattributes", ".gitignore", ".github/workflows/atlas-ci.yml", "tools/README.md",
        "tools/tools.schema.json", "LICENSE", "llms.txt", "CLAUDE.md", "AGENTS.md",
        "config/github-controls.json", "docs/CONSUMING.md",
        "tools/agent-task.schema.json", "tools/agent-task.example.json", "scripts/agentpolicy.py",
        "scripts/agentaudit.py", "scripts/agentrun.py", "scripts/agent_test.py",
        "scripts/packmanifest.py", "scripts/atlascore.py", "scripts/atlasgen.py", "scripts/ghaudit.py",
        "scripts/requirements.txt", "scripts/atlas_test.py", ".devcontainer/devcontainer.json", ".devcontainer/README.md",
        *REQUIRED_WIKI,
    ]
    for path in required:
        if not (ROOT / path).exists():
            errors.append(f"missing required path: {path}")


    aliases = [
        "docs/MODEL.md", "docs/PYTHON.md", "docs/RUST.md", "docs/GO.md", "docs/TYPESCRIPT.md",
        "models/agents/CANONICAL-MODEL.md",
    ]
    for alias in aliases:
        path = ROOT / alias
        if not path.is_symlink():
            errors.append(f"expected symlink: {alias}")
        elif not (path.parent / path.readlink()).exists():
            errors.append(f"broken symlink: {alias} -> {path.readlink()}")
    return errors


def dated_claim_errors() -> tuple[list[str], int, int]:
    """Every calendar date in a tracked text file, and the size of the sweep that found none.

    A DATE STAMPS WHEN SOMEONE TYPED; A VERSION STAMPS WHICH TREE THE CLAIM WAS TRUE OF. Only the
    second can be re-checked, and only the second survives being read a year later. So a calendar
    date may not appear in a tracked text file at all, with exactly two ways through: it is part of
    a URL, or it is an external project's own version that happens to be date shaped (MCP versions
    its specification that way), declared once in atlas.yaml.

    EXTRACTED BECAUSE THE RATCHET FIRED for the fourth time, on the line that wired the agent
    controls into check(). The cap falls with each split; raising it to fit the function it
    measures would make the ratchet a record of whatever happened last.
    """
    errors: list[str] = []
    external = {str(v) for v in (atlas().get("external_versions") or {}).values()}
    pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
    suffixes = {".md", ".yaml", ".yml", ".json", ".py", ".toml", ".txt"}
    scanned = 0
    for path in tracked():
        if path.suffix.lower() not in suffixes or path.is_symlink() or not path.exists():
            continue
        scanned += 1
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for token in line.split():
                found = pattern.search(token)
                if not found or token.startswith(("http://", "https://")) or found.group(0) in external:
                    continue
                errors.append(
                    f"calendar date in {rel(path)}:{number} ({found.group(0)}) — stamp the claim with the "
                    "contract version it was measured at, or declare the date as an external project's "
                    "version in atlas.yaml/external_versions")
    return errors, scanned, len(external)


def generated_errors(generator) -> tuple[list[str], int, int]:
    """Every generated block and generated file, against what the declaration would render now.

    EXTRACTED BECAUSE THE SHAPE RATCHET FIRED ON check() FOR THE FIFTH TIME — this run, on the one
    line that wired in the generated-file roster check. The cap falls with each split; raising it
    to fit the function it measures would make the ratchet a record of whatever happened last.
    """
    errors: list[str] = []
    ok = 0
    for name, (files, _) in generator.BLOCKS.items():
        block = generator.rendered(name)
        for rel_path in files:
            if block in read(rel_path):
                ok += 1
            else:
                errors.append(f"generated block '{name}' drifted or missing in {rel_path}: run `python scripts/atlas.py index --write`")
    for rel_path, builder in generator.GENERATED_FILES.items():
        if not (ROOT / rel_path).exists():
            errors.append(f"generated file missing: {rel_path}: run `python scripts/atlas.py index --write`")
        elif read(rel_path) != builder():
            errors.append(f"generated file drifted: {rel_path}: run `python scripts/atlas.py index --write`")
        else:
            ok += 1
    total = sum(len(f) for f, _ in generator.BLOCKS.values()) + len(generator.GENERATED_FILES)
    return errors + generator.generated_file_errors(), ok, total


def parse_errors() -> list[str]:
    """Every tracked artifact PARSES — source and configuration alike, and this runs first.

    Nothing below this check means anything otherwise. A source file that does not compile makes
    every document count a report about a tree that cannot run; a configuration file that does not
    load is a capability that silently does nothing while looking present to whoever wrote it.

    Both halves were earned. A mechanical re-indent wrote invalid Python twice and the contract
    printed all of its counts. Two host configurations carried an invalid JSON escape, so neither
    loaded at all and the tasks they declared had never run.
    """
    errors: list[str] = []
    # EVERY TRACKED SOURCE FILE MUST PARSE, AND THIS IS FIRST BECAUSE NOTHING BELOW IT IS
    # MEANINGFUL OTHERWISE. Measured cause: a mechanical re-indent of one function wrote a file
    # that no longer compiled, twice in a row, and the contract said nothing — it read documents
    # and rosters and never asked whether its own harness was still valid Python. A transformation
    # is not finished when the bytes are written; it is finished when the artifact parses.
    for path in tracked():
        if path.suffix != ".py" or path.is_symlink() or not path.exists():
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, ValueError) as exc:
            errors.append(f"{rel(path)} is not valid Python: {exc.__class__.__name__} "
                          f"at line {getattr(exc, 'lineno', '?')}")
    # EVERY TRACKED JSON PARSES, and this sits beside the Python parse check for the same reason:
    # a configuration file that does not parse is a capability that silently does nothing. Found by
    # trying — .vscode/tasks.json carried `"\${file}"`, an invalid JSON escape, so the whole file
    # failed to load and the task it declared had never worked. Editor configuration is JSONC by
    # convention, so it is read through the reader that understands comments and trailing commas.
    for path in tracked():
        if path.suffix.lower() not in {".json", ".example"} or path.is_symlink() or not path.exists():
            continue
        if path.suffix.lower() == ".example" and ".json" not in path.name:
            continue
        try:
            read_jsonc(rel(path))
        except ValueError as exc:
            errors.append(f"{rel(path)} is not valid JSON: {exc}")

    # AN UNCLOSED CODE FENCE SWALLOWS THE REST OF THE DOCUMENT. Everything after it renders as
    # code: the headings, the links, the tables. The file still parses, still passes a link check
    # if the swallowed links were already valid, and looks like a formatting preference rather
    # than a page that stopped working halfway down.
    for path in tracked():
        if path.suffix.lower() != ".md" or path.is_symlink() or not path.exists():
            continue
        fences = sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                     if line.startswith("```"))
        if fences % 2:
            errors.append(f"{rel(path)} has {fences} code fences — an odd count means one never "
                          "closes, and everything after it renders as code")
    return errors


def check() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    version = read("VERSION").strip()

    errors += parse_errors()
    # THE DECLARATION ITSELF IS FATAL RATHER THAN A ROW IN A LIST: if atlas.yaml does not parse,
    # every roster below is read from nothing and every count is a report about a tree that no
    # longer exists. So this returns from check(), which is why it cannot live in the helper.
    try:
        atlas()
    except ValueError as exc:
        print(f"Code-Development contract {version}: FAIL (atlas.yaml does not parse)")
        print(f"- {exc}")
        return 1

    if not LINK_RE.search("[self](self.md)"):
        errors.append("Markdown link parser self-test failed")

    for path in VERSION_SITES:
        if path != "atlas.yaml" and version not in read(path):
            errors.append(f"version mismatch: {path} != {version}")
    if str(atlas().get("version")) != version:
        errors.append(f"version mismatch: atlas.yaml {atlas().get('version')} != {version}")

    errors += required_path_errors()
    errors += cross_reference_errors()
    errors += agent_policy_errors() + authority_class_errors() + gate_tool_errors()
    errors += entry_cost_errors() + footprint_errors() + process_errors()
    errors += example_coverage_errors() + wheel_import_errors() + identity_errors()
    errors += mechanism_doc_errors()
    errors += generated_attribute_errors() + knowledge_errors() + action_errors() + claim_errors() + runner_errors()

    try:
        json.loads(read("config/github-labels.json"))
    except ValueError as exc:
        errors.append(f"config/github-labels.json does not parse: {exc}")

    # A DUPLICATE IN A LIST IS THE SAME COLLISION, HIDDEN WHERE THE LOADER CANNOT SEE IT. A second
    # `pip` entry for the same directory makes Dependabot's behaviour ambiguous, and YAML has no
    # duplicate to refuse because these are list items, not keys.
    seen_updates: set[tuple[str, str]] = set()
    for update in (yaml.safe_load(read(".github/dependabot.yml")) or {}).get("updates") or []:
        pair = (str(update.get("package-ecosystem")), str(update.get("directory")))
        if pair in seen_updates:
            errors.append(f"dependabot.yml declares {pair[0]} for {pair[1]} more than once")
        seen_updates.add(pair)

    route_map = routes()
    for suffix in (".py", ".rs", ".go", ".ts", ".ha", ".fut", ".carbon", ".roc", ".qs", ".sql", ".cu", ".lean"):
        if suffix not in route_map:
            errors.append(f"artifact route missing: {suffix}")
    targets = route_targets()
    labels = known_labels()
    manifests_present = cards_present = labelled = 0
    for target in targets:
        base = ROOT / "languages" / target
        if not (base / "README.md").exists():
            errors.append(f"route target missing: {target}")
        if (base / "OPERATING.md").exists():
            cards_present += 1
        else:
            errors.append(f"operating card missing: languages/{target}/OPERATING.md")
        if (base / "tools.yaml").exists():
            manifests_present += 1
            errors += manifest_errors(target)
        else:
            warnings.append(f"tool manifest missing (generic policy applies): languages/{target}/tools.yaml")
        if label_for(target) in labels:
            labelled += 1
        else:
            errors.append(f"route label not in config/github-labels.json: {label_for(target)}")

    model = read("MODEL.md")
    for adapter in re.findall(r"models/[A-Za-z0-9_-]+/README\.md", model):
        if not (ROOT / adapter).exists():
            errors.append(f"model adapter missing: {adapter}")

    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    for cls in CHANGE_CLASSES:
        req = (profiles.get(cls) or {}).get("required") if isinstance(profiles.get(cls), dict) else None
        if not isinstance(req, list) or not req:
            errors.append(f"verification_policy.profiles.{cls}.required missing or empty in atlas.yaml")
    date_errors, dated_scanned, external_count = dated_claim_errors()
    errors += date_errors

    # EVERY INSTRUMENT IS NAMED, AND EVERY LIMIT HAS AN OWNER. A roster of scripts maintained by
    # hand narrows the moment one is added beside it, and a limit recorded as prose belongs to
    # nobody. Both are structural here: an unlisted script and an empty `closed_by` fail.
    instruments = atlas().get("instruments") or {}
    script_files = sorted(ROOT.glob("scripts/*.py"))
    claimed = {str(spec.get("script")) for spec in instruments.values() if isinstance(spec, dict)}
    for name, spec in instruments.items():
        if not isinstance(spec, dict):
            errors.append(f"atlas.yaml/instruments/{name} is not a mapping")
            continue
        for field in ("script", "proves", "does_not_prove", "closed_by"):
            if not str(spec.get(field) or "").strip():
                errors.append(f"instrument '{name}' leaves '{field}' empty — a limit with no owner "
                              "is the blind spot this roster exists to make unrepresentable")
        script = str(spec.get("script") or "")
        if script and not (ROOT / script).exists():
            errors.append(f"instrument '{name}' names a file that does not exist: {script}")
    for path in script_files:
        if rel(path) not in claimed:
            errors.append(f"{rel(path)} is in the tree and named by no atlas.yaml/instruments entry")
    instruments_named = len(claimed & {rel(p) for p in script_files})

    decl_errors, decl_warnings = declaration_errors()
    errors += decl_errors
    warnings += decl_warnings

    task_profiles = atlas().get("task_profiles") or {}
    if not isinstance(task_profiles, dict) or "default" not in task_profiles:
        errors.append("atlas.yaml/task_profiles missing or has no 'default'")

    inbound: dict[str, list[str]] = {}
    links_checked = 0
    for source in tracked():
        if source.suffix.lower() != ".md" or source.is_symlink():
            continue
        try:
            content = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"non-UTF-8 markdown: {rel(source)}")
            continue
        for match in list(LINK_RE.finditer(content)) + list(HTML_LINK_RE.finditer(content)):
            raw = (match.group(1) if match.re is HTML_LINK_RE
                   else (match.group(1) or match.group(2))) or ""
            try:
                target = link_target(source, raw)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if target is None:
                continue
            links_checked += 1
            key = rel(target)
            inbound.setdefault(key, []).append(rel(source))
            if target.is_dir():  # a link to a directory reaches its README
                inbound.setdefault(key + "/README.md", []).append(rel(source))
            if not target.exists():
                errors.append(f"broken local link: {rel(source)} -> {raw}")

    generator, inv = _selfcheck()
    gen_errors, blocks_ok, blocks_total = generated_errors(generator)
    errors += gen_errors

    guides_total = guides_indexed = 0
    for guide in (ROOT / "languages").rglob("README.md"):
        guide_rel = rel(guide)
        if guide_rel == "languages/README.md":
            continue
        guides_total += 1
        if guide_rel in inbound:
            guides_indexed += 1
        else:
            errors.append(f"unindexed language guide: {guide_rel}")

    for root_name in ORPHAN_ROOTS:
        for path in (ROOT / root_name).rglob("*.md"):
            path_rel = rel(path)
            if path.is_symlink() or path.name == "README.md" or path_rel in EXEMPT:
                continue
            if path_rel not in inbound:
                errors.append(f"orphaned durable document: {path_rel}")

    for workflow in (ROOT / ".github" / "workflows").glob("*.y*ml"):
        content = workflow.read_text(encoding="utf-8")
        if "permissions:" not in content:
            errors.append(f"workflow missing permissions: {rel(workflow)}")
        if "concurrency:" not in content:
            errors.append(f"workflow missing concurrency: {rel(workflow)}")
        if "pull_request_target:" in content:
            errors.append(f"privileged trigger requires review: {rel(workflow)}")

    file_errors, file_warnings = tracked_file_errors()
    errors += file_errors
    warnings += file_warnings

    inv_violations, inv_enforced, inv_declared = inv.invariants()
    errors += inv_violations

    counts = (f"links {links_checked} | routes {len(targets)} | guides {guides_indexed}/{guides_total} | "
              f"cards {cards_present}/{len(targets)} | manifests {manifests_present}/{len(targets)} | "
              f"labels {labelled}/{len(targets)} | generated {blocks_ok}/{blocks_total} | "
              f"instruments {instruments_named}/{len(script_files)} | "
              f"dated claims 0 in {dated_scanned} text files ({external_count} external versions declared) | "
              f"invariants {len(inv_enforced)} enforced + {len(inv_declared)} declared"
              f"/{len(atlas().get('hard_invariants') or [])} | warnings {len(set(warnings))}")
    if errors:
        print(f"Code-Development contract {version}: FAIL ({len(set(errors))} errors)")
        print("\n".join(f"- {e}" for e in sorted(set(errors))))
        print(counts)
        return 1
    print(f"Code-Development contract {version}: OK")
    print(counts)
    if warnings:
        print("warnings (non-blocking):")
        print("\n".join(f"- {w}" for w in sorted(set(warnings))))
    return 0


def route_record(path_value: str) -> dict:
    """The route as DATA. An agent parsing printed lines re-implements the router by regex."""
    language, rule, evidence = route_with_evidence(path_value)
    record: dict[str, object] = {
        "schema": 1, "command": "route", "path": path_value,
        "route": language, "resolved_by": rule, "evidence": evidence,
        # WHAT THIS ROUTER DOES NOT DECIDE. atlas.yaml declares six precedence rules and this
        # implementation resolves two; the other four belong to the caller — an explicit override,
        # a project manifest, an issue label, a generic fallback. Until 2.12.0 a consumer had no
        # way to learn that from the record, so it could read `resolved_by: artifact_extension` and
        # never know a manifest rule ABOVE it was never consulted. A silently skipped precedence
        # level is the same defect as a silently skipped test.
        "precedence": [
            {"rule": name, "resolved_here": name in PRECEDENCE_IMPLEMENTED}
            for name in ((atlas().get("routing_policy") or {}).get("precedence") or [])],
    }
    if not language:
        return record
    base = ROOT / "languages" / language
    manifest = yaml.safe_load((base / "tools.yaml").read_text(encoding="utf-8")) if (base / "tools.yaml").exists() else {}
    record.update({
        "guide": f"languages/{language}/README.md",
        "operating_card": f"languages/{language}/OPERATING.md",
        "tool_manifest": f"languages/{language}/tools.yaml",
        "manifest_present": bool(manifest),
        "authority": (manifest or {}).get("authority", {}),
        # WHICH CLAIM EACH TOOL SUPPORTS. A flat map of roles invites the reading that a green
        # compiler answers for behaviour; this splits it, and the classes with NO tool are the
        # half worth printing — they say what this pack cannot answer rather than implying it can.
        "authority_by_class": {
            name: {role: (manifest or {}).get("authority", {}).get(role)
                   for role in (spec or {}).get("roles") or []}
            for name, spec in (atlas().get("authority_classes") or {}).items()},
        "authority_gaps": {
            name: str((spec or {}).get("closed_by"))
            for name, spec in (atlas().get("authority_classes") or {}).items()
            if not ((spec or {}).get("roles") or [])},
        "default_tools": ((manifest or {}).get("policy") or {}).get("default_tools", []),
        "label": label_for(language),
        "branch_lane": f"lang/{language}/<topic>",
        "worktree": f"../Code-Development-wt/{language.replace('/', '-')}-<topic>",
        "runtime": "models/vscode/README.md",
        "mcp": "integrations/MCP-LANGUAGE-MATRIX.md",
        "operations": "wiki/LANGUAGE-OPERATIONS.md",
        "verification": "docs/VERIFY.md",
    })
    return record


def route(path_value: str, as_json: bool = False) -> int:
    record = route_record(path_value)
    if as_json:
        print(json.dumps(record, indent=2, sort_keys=False))
        return 0 if record["route"] else 2
    if not record["route"]:
        print(f"no Atlas route for {path_value}")
        print(f"why: {record['evidence']}")
        return 2
    language = record["route"]
    manifest = str(record["tool_manifest"])
    if not record["manifest_present"]:
        manifest += " (MISSING — generic tool policy applies; see tools/README.md)"
    print(f"language/domain: {language}")
    print(f"resolved by: {record['resolved_by']}")
    caller = [p["rule"] for p in record["precedence"] if not p["resolved_here"]]
    print(f"resolved by the CALLER, not here: {', '.join(caller)}")
    print(f"evidence: {record['evidence']}")
    print(f"guide: {record['guide']}")
    print(f"operating card: {record['operating_card']}")
    print(f"tool manifest: {manifest}")
    for name, tools in (record.get("authority_by_class") or {}).items():
        named = ", ".join(f"{r}={v}" for r, v in tools.items() if v)
        print(f"authority [{name}]: {named or 'none declared by this pack'}")
    for name, closer in (record.get("authority_gaps") or {}).items():
        print(f"NOT answered by any tool in this pack [{name}]: {closer}")
    print(f"runtime: {record['runtime']}")
    print(f"mcp: {record['mcp']} -> use only the justified profile")
    print(f"operations: {record['operations']}")
    print(f"issue label: {record['label']}")
    print(f"branch lane: {record['branch_lane']} (temporary; merge to main)")
    print(f"worktree: {record['worktree']}")
    print(f"verify: {record['verification']}")
    return 0


def plan(path_value: str, task: str, change: str | None, as_json: bool = False,
         modifiers: list[str] | None = None) -> int:
    language = route_for(path_value)
    profiles = atlas().get("task_profiles") or {}
    gates = (atlas().get("verification_policy") or {}).get("profiles") or {}
    tiers = (atlas().get("verification_policy") or {}).get("tiers") or {}
    if not language:
        print(f"no Atlas route for {path_value}")
        return 2
    if task not in profiles:
        print(f"unknown task profile: {task}")
        print("available: " + ", ".join(profiles))
        return 2
    record = plan_record(path_value, language, task, change, modifiers)
    if as_json:
        print(json.dumps(record, indent=2, sort_keys=False))
        return 0
    return plan_text(record, language, task, change, modifiers, gates, tiers)


def plan_record(path_value: str, language: str, task: str, change: str | None,
                modifiers: list[str] | None) -> dict:
    """The plan as DATA — one producer, so tools/atlas-output.schema.json can be asserted over it."""
    profiles = atlas().get("task_profiles") or {}
    gates = (atlas().get("verification_policy") or {}).get("profiles") or {}
    tiers = (atlas().get("verification_policy") or {}).get("tiers") or {}
    return {
        "schema": 1, "command": "plan", "path": path_value, "route": language, "task": task,
        "tools": list(profiles[task]),
        "change_class": change,
        "risk_modifiers": list(modifiers or []),
        # A MODIFIER ONLY EVER ADDS. The class stays the floor, so selecting one can never buy a
        # cheaper run — which is the only property that makes a modifier safe to offer at all.
        "required_gates": required_gates({"change_class": change, "risk_modifiers": modifiers or []})
                          if change else None,
        "risk_modifier_catalog": {name: str((spec or {}).get("applies_to"))
                                  for name, spec in (atlas().get("risk_modifiers") or {}).items()},
        "change_classes": list(gates),
        "verification_tiers": list(tiers),
        "guide": f"languages/{language}/README.md",
        "operating_card": f"languages/{language}/OPERATING.md",
        "tool_manifest": f"languages/{language}/tools.yaml",
        "verification": "docs/VERIFY.md",
        "branch_policy": "wiki/BRANCH-WORKTREES.md",
    }


def plan_text(record: dict, language: str, task: str, change: str | None,
              modifiers: list[str] | None, gates: dict, tiers: dict) -> int:
    """The same record, rendered. A reader gets prose; a consumer gets the record."""
    print(f"language/domain: {language}")
    print(f"guide: {record['guide']}")
    print(f"operating card: {record['operating_card']}")
    print(f"tool manifest: {record['tool_manifest']}")
    print(f"task: {task}")
    print("tools:")
    for tool in record["tools"]:
        print(f"- {tool}")
    if change:
        floor = set((gates.get(change) or {}).get("required") or [])
        print(f"required gates ({change}" + (f" + {', '.join(modifiers or [])}" if modifiers else "") + "):")
        for gate in record["required_gates"] or []:
            argv, why = gate_command(language, gate)
            source = "class" if gate in floor else "modifier"
            print(f"- {gate} [{source}] -> " + (" ".join(argv) if argv else f"NOT RUNNABLE HERE ({why})"))
        offered = [n for n, applies in record["risk_modifier_catalog"].items()
                   if applies == change and n not in (modifiers or [])]
        if offered:
            print("risk modifiers available for this class: " + ", ".join(sorted(offered)))
    else:
        print("required gates: pass --change <" + "|".join(record["change_classes"]) + ">")
    print("verification tiers: " + " -> ".join(record["verification_tiers"])
          if record["verification_tiers"] else "verification tiers: none declared in atlas.yaml")
    print(f"verification: {record['verification']} + applicable native language checks")
    print(f"branch/worktree: {record['branch_policy']}")
    return 0


def learn(language: str) -> int:
    """Turn an operating card into the seven-pass mastery loop (research/LANGUAGE-MASTERY.md)."""
    target = language if (ROOT / "languages" / language / "OPERATING.md").exists() else route_for(language)
    if not target or not (ROOT / "languages" / target / "OPERATING.md").exists():
        print(f"no operating card for {language}")
        return 2
    card = read(f"languages/{target}/OPERATING.md")
    def field(name: str) -> str:
        m = re.search(rf"\*\*{name}:\*\*\s*(.+)", card)
        return m.group(1).strip() if m else "(not on the card)"
    manifest_path = ROOT / "languages" / target / "tools.yaml"
    tools = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    raw_auth = tools.get("authority", {})
    # A role may declare several tools that are needed TOGETHER; render it as such.
    auth = {k: " + ".join(str(i) for i in v) if isinstance(v, list) else v for k, v in raw_auth.items()}
    verify = (tools.get("provenance") or {}).get("verify") or []
    print(f"language: {target}")
    print(f"card: languages/{target}/OPERATING.md")
    print(f"fast path: {field('Fast path')}")
    print(f"native authority: {field('Native authority')}")
    print(f"research: {field('Research')}")
    print("mastery loop (one pass each, record the lesson at the end):")
    steps = [
        ("read reference", f"docs {auth.get('docs', '(none)')}"),
        ("trace real code", f"research {auth.get('research', '(none)')}"),
        ("reproduce a tiny example", f"run with {auth.get('compiler_or_runtime', '(none)')}"),
        ("modify it", f"format with {auth.get('formatter', 'none')}; language server {auth.get('lsp', 'none')}"),
        ("break it on purpose", f"tests {auth.get('test', 'none')}; fuzz {auth.get('fuzz', 'none')}"),
        ("verify", f"security {auth.get('security', 'none')}; debugger {auth.get('debugger', 'none')}"),
        ("benchmark", f"profiler {auth.get('profiler', 'none')}"),
        ("record the lesson", "one fact per note; a measured number beats a summary"),
    ]
    for i, (step, how) in enumerate(steps, 1):
        print(f"  {i}. {step}: {how}")
    if verify:
        print("confirm before relying on: " + ", ".join(verify))
    print(f"avoid: {field('Avoid')}")
    return 0


def do(path_value: str, action: str | None, execute: bool) -> int:
    """`atlas do <file> <action>` — the pack's own tool, resolved and PRINTED before it is run.

    Printing is the default and running is opt-in, because this resolves a command from a
    declaration and the reader should see which one before it touches their tree.
    """
    language = route_for(path_value)
    if not language:
        print(f"no Atlas route for {path_value}")
        return 2
    actions = atlas().get("pack_actions") or {}
    if action is None:
        print(f"{path_value} -> {language}")
        for name in sorted(actions):
            argv, why_not = action_command(language, name, path_value)
            print(f"  {name:<9} " + (" ".join(argv) if argv else f"unavailable — {why_not}"))
        return 0
    argv, reason = action_command(language, action, path_value)
    if argv is None:
        print(f"cannot run '{action}' for {language}: {reason}")
        return 2
    verdict = command_verdict({"allowed_commands": [argv[0].rsplit("/", 1)[-1]]}, argv)
    if not verdict.allowed:
        print(f"refused by the declared floor [{verdict.control}]: {verdict.reason}")
        return 2
    print(f"{language} {action} ({reason}): {' '.join(argv)}")
    if not execute:
        print("not run — add --run to execute it")
        return 0
    return subprocess.run(argv, cwd=ROOT, check=False).returncode


def process(name: str | None, as_json: bool) -> int:
    """`atlas process <id>` — the external reference for a named process."""
    registry = atlas().get("processes") or {}
    if name is None:
        for key, spec in sorted(registry.items()):
            print(f"{key:<20} profile {spec.get('task_profile'):<18} class {spec.get('change_class')}")
        print(f"{len(registry)} processes; `atlas process <id> --json` for one")
        return 0
    if name not in registry:
        print(f"unknown process: {name}")
        print("available: " + ", ".join(sorted(registry)))
        return 2
    record = process_record(name)
    if as_json:
        print(json.dumps(record, indent=2, sort_keys=False))
        return 0
    print(f"process: {record['process']} (atlas {record['atlas_version']})")
    print(f"task profile: {record['task_profile']} -> {', '.join(record['tools'])}")
    print(f"change class: {record['change_class']}")
    for step in record["sequence"]:
        print(f"  {step['step']:<14} {step['means']}")
    print("required gates: " + ", ".join(record["required_gates"]))
    print("artifacts: " + ", ".join(record["artifacts"]))
    print("STOP when: " + ", ".join(record["stop_when"]))
    print("ESCALATE when: " + ", ".join(record["escalate_when"]))
    print(f"task contract schema: {record['task_contract_schema']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atlas.py")
    sub = parser.add_subparsers(dest="command", required=True)
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--fix", action="store_true",
                              help="repair what is MECHANICAL — regenerate drifted blocks, tighten a "
                                   "ratchet to what the tree costs — then re-check. It never raises a "
                                   "bound and never repairs a decision")
    sub.add_parser("invariants")
    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true", help="emit the environment as a record")
    index_parser = sub.add_parser("index")
    index_parser.add_argument("--write", action="store_true")
    learn_parser = sub.add_parser("learn")
    learn_parser.add_argument("language", help="a route (python, quantum/qsharp) or a file to route")
    process_parser = sub.add_parser("process")
    process_parser.add_argument("id", nargs="?", default=None, help="a key of atlas.yaml/processes")
    process_parser.add_argument("--json", action="store_true", help="emit the process as a JSON record")
    index_parser = sub.add_parser("index-search")
    index_parser.add_argument("query", nargs="+")
    index_parser.add_argument("--limit", type=int, default=5)
    do_parser = sub.add_parser("do")
    do_parser.add_argument("path")
    do_parser.add_argument("action", nargs="?", default=None, help="a key of atlas.yaml/pack_actions")
    do_parser.add_argument("--run", action="store_true", help="execute it; printing is the default")
    pick_parser = sub.add_parser("pick")
    pick_parser.add_argument("axis", nargs="?", default=None, help="a key of atlas.yaml/language_selection")
    why_parser = sub.add_parser("why")
    why_parser.add_argument("id", nargs="?", default=None, help="a key of atlas.yaml/asymmetries")
    route_parser = sub.add_parser("route")
    route_parser.add_argument("path")
    route_parser.add_argument("--json", action="store_true", help="emit the route as a JSON record")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("path")
    plan_parser.add_argument("--task", default="default", help="a key of atlas.yaml/task_profiles")
    plan_parser.add_argument("--change", default=None, help="a key of atlas.yaml/verification_policy/profiles")
    plan_parser.add_argument("--modifier", action="append", default=[], dest="modifiers",
                             help="a key of atlas.yaml/risk_modifiers; repeatable, and it only ADDS gates")
    plan_parser.add_argument("--json", action="store_true", help="emit the plan as a JSON record")
    args = parser.parse_args(argv)
    if args.command == "check":
        if not args.fix:
            return check()
        # REPAIR, THEN RE-CHECK, AND THE SECOND RUN IS THE VERDICT. A fixer that reports its own
        # success is a fixer nobody verified; the exit code comes from the check, not from here.
        generator, _ = _selfcheck()
        generator.index(write=True)
        for line in tighten_ratchets(write=True):
            print(f"tightened  {line}")
        atlas.cache_clear()
        print("repaired what is mechanical; a broken link, an unowned invariant or a missing "
              "example is a DECISION and is left to whoever reads the diff")
        return check()
    if args.command == "invariants":
        _, inv = _selfcheck()
        violations, enforced, declared = inv.invariants()
        for name in enforced:
            problem = inv.INVARIANT_CHECKS[name]()
            print(f"ENFORCED  {name}" + (f"  -> VIOLATED: {problem}" if problem else ""))
        for name in declared:
            print(f"DECLARED  {name}: {inv.INVARIANT_DECLARED[name]}")
        print(f"{len(enforced)} enforced, {len(declared)} declared, {len(violations)} unowned or violated")
        return 1 if violations else 0
    if args.command == "doctor":
        return doctor_main(["--json"] if args.json else [])
    if args.command == "index":
        generator, _ = _selfcheck()
        return generator.index(args.write)
    if args.command == "learn":
        return learn(args.language)
    if args.command == "index-search":
        from atlasindex import main as index_main
        return index_main(["search", *args.query, "--limit", str(args.limit)])
    if args.command == "do":
        return do(args.path, args.action, args.run)
    if args.command == "pick":
        return pick(args.axis)
    if args.command == "why":
        return why(args.id)
    if args.command == "process":
        return process(args.id, args.json)
    if args.command == "route":
        return route(args.path, args.json)
    return plan(args.path, args.task, args.change, args.json, args.modifiers)


if __name__ == "__main__":
    raise SystemExit(main())
