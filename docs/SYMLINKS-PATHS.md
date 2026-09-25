# Symlinks and Paths

Symlinks are useful for developer topology and compatibility but are not a security boundary.

Prefer relative links, predictable targets, no secret symlinks, short chains, and CI/container testing.

Inspect with:
```bash
git ls-files -s
readlink path/to/link
realpath path/to/link
```

For untrusted paths: `input -> normalize -> resolve -> verify allowed root -> operate`.

Git stores symlinks with mode `120000`; the blob contains the link target.
