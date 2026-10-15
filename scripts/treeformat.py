"""Working-tree formatting and blame-history checks."""

import re
import subprocess


def editorconfig_errors() -> list[str]:
    """Every tracked text file obeys what the .editorconfig sections matching it declare.

    MEASURED at 2.27.0: the contract checked that .editorconfig EXISTED and nothing checked that
    any file obeyed it — 34 tracked files lacked the final newline it requires, and one had
    trailing whitespace from an edit made the same session. A declared control no instrument reads
    is a comment with a file extension. The rules are READ from the file, so editing .editorconfig
    changes what is enforced with no second copy here to update.
    """
    import configparser as _cp  # noqa: PLC0415 — only this check reads INI
    import fnmatch  # noqa: PLC0415

    from atlascore import ROOT, read, tracked

    parser = _cp.ConfigParser(interpolation=None)
    try:
        parser.read_string(read(".editorconfig").replace("root = true", "", 1))
    except _cp.Error as exc:
        return [f".editorconfig does not parse: {exc}"]
    # EVERY SECTION, resolved per file in file order, later wins (3.50.0): only [*] was read, so
    # `indent_style = space` and `charset` were declared for every route and enforced for none.
    sections = []
    for pattern in parser.sections():
        brace = re.fullmatch(r"(.*)\{(.*)\}(.*)", pattern)
        globs = [brace[1] + alt + brace[3] for alt in brace[2].split(",")] if brace else [pattern]
        sections.append((globs, dict(parser[pattern])))
    binary = {".webp", ".png", ".jpg", ".ico", ".gz", ".zip"}
    errors: list[str] = []
    for path in tracked():
        name = path.relative_to(ROOT).as_posix()
        if (
            not path.is_file()
            or path.is_symlink()
            or path.suffix.lower() in binary
            or name.endswith((".bat", ".cmd", ".ps1"))
        ):
            continue  # binary, or a Windows script whose own section declares crlf
        raw = path.read_bytes()
        if not raw:
            continue
        rules: dict[str, str] = {}
        for globs, values in sections:
            if any(fnmatch.fnmatch(path.name, glob) for glob in globs):
                rules.update(values)
        if rules.get("insert_final_newline") == "true" and not raw.endswith(b"\n"):
            errors.append(f"{name} has no final newline, which .editorconfig requires")
        if rules.get("end_of_line") == "lf" and b"\r\n" in raw:
            errors.append(f"{name} has CRLF line endings, which .editorconfig forbids")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            text = raw.decode("utf-8", "replace")
            if rules.get("charset") == "utf-8":
                errors.append(f"{name} is not UTF-8 (byte {exc.start}), which .editorconfig requires")
        lines = text.split("\n")
        # Markdown is exempt from the whitespace rule BY FORMAT: two trailing spaces are a hard
        # line break there, so stripping them would change the rendered document.
        if (
            rules.get("trim_trailing_whitespace") == "true"
            and not name.endswith(".md")
            and any(line != line.rstrip(" \t") for line in lines)
        ):
            errors.append(f"{name} has trailing whitespace, which .editorconfig forbids")
        if rules.get("indent_style") == "space" and (
            tab := next((n for n, ln in enumerate(lines, 1) if ln.startswith("\t")), 0)
        ):
            errors.append(f"{name}:{tab} is tab-indented, and .editorconfig declares indent_style = space")
    return errors


def blame_ignore_errors() -> list[str]:
    """`.git-blame-ignore-revs` names commits ON THIS HISTORY. Found at 3.50.0: a rebase-merge
    rewrote the formatting commit, the file kept the pre-rebase hash, and blame skipped nothing
    while the file looked correct. A shallow clone cannot answer, so it is refused, never passed."""
    from atlascore import ROOT

    path = ROOT / ".git-blame-ignore-revs"
    if not path.is_file():
        return [".git-blame-ignore-revs is missing, so a mechanical reformat is blamed on its author"]
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    shas = [ln for ln in lines if ln and not ln.startswith("#")]
    errors = [
        f".git-blame-ignore-revs: {sha!r} is not a full 40-hex commit"
        for sha in shas
        if not re.fullmatch(r"[0-9a-f]{40}", sha)
    ]
    git = ["git", "-C", str(ROOT)]
    shallow = subprocess.run(
        [*git, "rev-parse", "--is-shallow-repository"], capture_output=True, text=True, check=False, timeout=20
    )
    if shallow.stdout.strip() != "false":
        return [
            *errors,
            ".git-blame-ignore-revs: shallow or no history, so its commits were NOT checked (fetch-depth: 0)",
        ]
    for sha in (s for s in shas if re.fullmatch(r"[0-9a-f]{40}", s)):
        if subprocess.run(
            [*git, "merge-base", "--is-ancestor", sha, "HEAD"], capture_output=True, check=False, timeout=20
        ).returncode:
            errors.append(
                f".git-blame-ignore-revs: {sha} is not an ancestor of HEAD — a rebase rewrote it; name the landed hash"
            )
    return errors
