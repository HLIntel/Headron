# Dependencies — what an install really pulls in

A dependency count is only honest when it is the **closure**: everything an install fetches and
runs, not the lines someone typed. "One dependency" is a false minimum the day that dependency
gains dependencies of its own.

## The four things this page means by "dependency"

- **Direct** — what a manifest names. The number people quote, and the least informative one.
- **Transitive** — what the direct ones pull in, recursively. This is what an install runs, and
  what an attacker reaches.
- **Micro** — a package of a few lines that still arrives with its own maintainer, release channel
  and install-time code. Each one is a new party you trust, for very little function.
- **Wiring** — this repository's own modules and which may import which. A shipped module that
  imports a development-only one breaks every consumer, silently, at import time.

## Why a small direct count misleads (REPORTED)

- **The average npm package trusts about 80 others.** Installing one implicitly trusts 79
  third-party packages and 39 maintainers through transitive dependencies — Zimmermann et al.,
  [*Small World with High Risks*](https://www.usenix.org/system/files/sec19-zimmermann.pdf),
  USENIX Security 2019.
- **A trusted package gained one new dependency, and that dependency turned malicious.** event-stream
  added `flatmap-stream` under a caret range. A later patch release of it carried the payload, and
  every fresh install of event-stream fetched it without a single change on the consumer's side —
  [npm's analysis](https://blog.npmjs.org/post/180565383195/details-about-the-event-stream-incident)
  · [Snyk's post-mortem](https://snyk.io/blog/a-post-mortem-of-the-malicious-event-stream-backdoor/).
- **The attack travels the graph, not the manifest.** A backdoor in a compression library reached
  remote login on affected Linux systems through a chain of system libraries nobody had listed as a
  dependency of it — [CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094).

## How this repository holds its own line

- **The closure is declared and enforced.** `atlas.yaml/context_policy/install_footprint/resolved_closure`
  states what an install pulls in. The invariant `dependency_count_is_the_closure` fails the build
  when that disagrees with the hash lock, or when walking installed package metadata finds anything
  the lock does not pin.
- **The lock is the closure.** `scripts/requirements.lock.txt` is hash-pinned and CI installs it with
  hashes required, so anything unpinned is refused rather than fetched.
- **The pull request diffs the graph.** Dependency Review is a required check, and it denies
  licences that would change what the whole tree may be used for.
- **The wiring has one direction.** `pyproject.toml` lists what ships. `atlas.py check` refuses a
  script that is in neither the shipped list nor the development-only list, and refuses a shipped
  module importing a development-only one at module level.

## Ask the atlas, per language

```bash
python scripts/atlas.py gate <file> dependency_graph     # the pack's command that prints the full tree
python scripts/atlas.py gate <file> vulnerability_scan   # its built-in audit, or who covers the gap
python scripts/atlas.py plan <file> --task implementation --change dependency_change --json
```

Each gate answers with the pack's own built-in command, or **absent** and the control that covers
it. It never hands back a bare tool name: a package manager's name, run alone, proves nothing.

## When building: get the most from the fewest parties

1. **Climb the ladder first:** needed at all → already in this tree → standard library → platform →
   an installed dependency → one line of your own. A new package is the last rung.
2. **Count the closure before you add.** Run the `dependency_graph` gate before and after, and read
   the difference. That difference is what you are accepting, not the one line in the manifest.
3. **Prefer one maintained package to many micro ones.** Copying a ten-line function, with its
   licence, removes a maintainer, a release channel and an install hook from the trust set.
4. **Pin exactly, lock with hashes, bound the range.** A caret range is permission for a stranger to
   change your build tomorrow. That is the event-stream path.
5. **Review the lock diff, not only the manifest diff.** The manifest shows one line. The lock shows
   everything that line brought with it.
6. **Delete what nothing imports.** An unused dependency is still installed, still trusted and still
   a way in.
7. **Declare the number, then enforce it.** A count in a README is a claim. A count held to the
   lock by the build is a measurement.

## What this page does not prove

That any dependency is safe. It proves only that the count is the real count and that every change
to it is visible and reviewed. Safety is still the reviewer's call, per change.
