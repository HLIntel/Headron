# Git object identity, in-process

`scripts/gitobject.py` computes a Git blob's name in the Python process that needs it: the hash of
`blob <byte length>\0<content>`. It also owns what an object id looks like, in both object formats.

## What a match proves

A matching blob name proves the bytes hashed are the bytes named. Accidental corruption and a plain edit are caught.

It does not prove:

- **Who wrote the bytes.** A hash carries no author, and anyone can hash anything. Authorship is a signature's job.
- **That a SHA-1 name is unique.** SHA-1 is not collision-resistant. Python's `hashlib` has no collision detection, while
  the Git measured here reports `SHA-1: SHA1_DC`. Two crafted files can share a name in this module that such a Git
  would refuse. A SHA-256 repository does not have this weakness.
- **That Git would store these bytes.** `path_oid` matches `git hash-object --no-filters`. A clean filter or text
  conversion changes content before Git hashes it, so a working file can differ from its blob and still be unchanged.
- **Anything about an object in a pack or an alternate.** `verify-staged` reads loose objects only and counts the rest as
  unchecked. A caller must read that count; a pass with most objects unchecked is not a repository-wide result.
- **Anything about a tree or a commit.** This module hashes blobs. A tree hasher needs a differential test against Git,
  including the rule that sorts a directory as if its name ended in `/`: `git hash-object -t tree` refuses a tree in any
  other order.

## Measurements

Measured on one Mac with Git 2.54.0 (Apple Git-157). Each number is a single run's result, not a benchmark suite. The
in-process times include reading the file.

| Operation                                    | In-process  | Spawned Git                                  |
| -------------------------------------------- | ----------- | -------------------------------------------- |
| One small file, median (n=40)                | 17 µs       | 9.79 ms per `git hash-object`, 18.49 ms max  |
| 568 files, 5.9 MB, in bulk, measured at 3.61 | 37.6 ms     | 40.0 ms with `git hash-object --stdin-paths` |
| Names that disagreed across those files      | 0           | n/a                                          |
| 50 MB through `hashlib`, measured at 3.61    | SHA-1 20 ms | SHA-256 19 ms, also in-process               |

The speed win holds only against one spawn per file. In bulk, the two tie, because `--stdin-paths` keeps one process.

`verify-staged` on this repository takes a median 28.1 ms (max 35, n=15). In that run it re-hashed 1 staged blob and
left 572 entries unchecked (measured at 3.61), because they were in a pack or absent. `git fsck --connectivity-only` takes 75 ms and does
not hash, so the two are not comparable.

Unmeasured: a full `git fsck` on this repository.

## Where the time in a hook goes

The hash is not the hot path. The pre-commit rungs measured:

| Rung               | Time    | Git spawns           |
| ------------------ | ------- | -------------------- |
| `atlas check`      | 4051 ms | 14, none hash-object |
| `astshape`         | 1191 ms | not counted          |
| `contextcost`      | 1271 ms | 2                    |
| `enforce --staged` | 101 ms  | 1                    |
| `mdshape --staged` | 118 ms  | 3                    |

Each runs inside `uv run --frozen`, which costs about 0.45 s, and starting `python -I -S` costs about 10 ms. Removing
one `git hash-object` from a commit saves about 10 ms of several seconds, so `verify-staged` is a prototype command and
is not wired into `.githooks/pre-commit`.

`mdshape.py` keeps `git hash-object <path>`: the path form applies filters, which is the question it asks.

## The bug the work found

`.githooks/pre-push` and `claude_hook.py` compared a remote ref with forty zeros, written by hand. In a SHA-256
repository an absent object is sixty-four zeros, so pre-push refused a new lane as "non-fast-forward" and refused a
delete outright. Both failed closed and gave the wrong reason. A new lane now fails with the right reason, and a delete
passes, in both formats.

Five sites held the same assumption. `gitobject` owns the shape now, and the invariant `object_ids_are_format_agnostic`
refuses a new one, as text, because shell and JSON hold ids too. It does not match a bare `[:40]` slice or
`sha(v, 40)`.

## Usage

```bash
python scripts/gitobject.py verify-staged
```

Exit 0 means every loose staged blob matched and the output counts what went unchecked. Exit 1 means a mismatch. Exit 2
means the repository could not be read.
