#!/usr/bin/env python3
"""vaultlinks — Obsidian graph health, measured the way Obsidian actually resolves.

WHY THIS EXISTS: measured at contract 3.23.1: a first pass resolved wikilinks by STEM only. It
reported 189 ambiguous links that do not exist (a path-qualified
`[[wallets/0x4a449c25]]` is unambiguous) and it could not tell a path-qualified
hit from a miss. A resolver that does not implement the target system's rule
measures its own bug. Obsidian resolves a link by (a) exact relative path or
(b) a unique leaf filename anywhere in the vault — both are implemented here.

Prints COVERAGE and its BLIND SPOTS every run: a clean pass is never read as
more than it is. Exit 0 always — this REPORTS, it does not gate. Marking a dead
pointer is a judgement call about history, not a fault to fail a build on.
"""
import collections
import os
import re
import sys
from pathlib import Path

V = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ.get('VAULT', Path.cwd()))
SKIP = {'.obsidian', '.smart-env', '.git', '.trash', 'graphify-out'}
# Folders whose notes are islands BY DESIGN (daily logs, archives). Override with
# VAULT_TERMINAL='Daily,Archive' — a comma list matched as substrings of the path.
TERMINAL = tuple(f for f in os.environ.get('VAULT_TERMINAL', 'DAILY NOTES,ARCHIVE').split(',') if f)

files = []
others = set()   # a non-note file is linked by its full name: [[Vault-Health.base]], [[deck.pdf]]
for r, d, f in os.walk(V):
    d[:] = [x for x in d if x not in SKIP]
    files += [Path(r) / n for n in f if n.endswith('.md')]
    others.update(n for n in f if not n.endswith('.md'))
rel = {str(p.relative_to(V).with_suffix('')) for p in files}
stems = collections.defaultdict(list)
for p in files:
    stems[p.stem].append(p)

FENCE = re.compile(r'```.*?```', re.S)      # a [[link]] inside a code fence is not a link
INLINE = re.compile(r'`[^`\n]*`')
LINK = re.compile(r'(?<!!)\[\[([^\[\]]+?)\]\]')   # (?<!!) drops ![[embeds]]

out = collections.defaultdict(set)
inn = collections.defaultdict(set)
dang = collections.Counter()
amb = collections.Counter()
total = 0

def resolve(tgt):
    """Obsidian's rule, and ORDER MATTERS. A first version tried the path-suffix
    match first, so a BARE `[[CLUSTER-MAP]]` matched `.../CLUSTER-MAP` and returned
    unambiguous — it reported 0 ambiguous links while a peer session independently
    counted 29. A bare target has no path to match, so it must go down the
    stem-uniqueness branch; only a target CONTAINING '/' is a path reference."""
    if '/' in tgt:
        for r in rel:
            if r == tgt or r.endswith('/' + tgt):
                return V / (r + '.md'), False
    hits = stems.get(tgt.split('/')[-1], [])
    if not hits:
        return None, False
    # AMBIGUOUS means the AUTHOR left it ambiguous: a BARE link whose stem is not
    # unique. A path-qualified target that misses its path and then resolves by leaf
    # is a WRONG path, not a coin flip — counting it here inflated 52 refs to 94.
    return hits[0], (len(hits) > 1 and '/' not in tgt)

for p in files:
    body = INLINE.sub(' ', FENCE.sub(' ', p.read_text(errors='ignore')))
    for m in LINK.findall(body):
        # A TABLE ESCAPES THE PIPE (3.43.0): `[[X\|alias]]` inside a Markdown table resolves to X in
        # Obsidian, and reading `X\` as the target reported 11 working links dangling.
        tgt = m.split('|')[0].split('#')[0].strip().rstrip('\\').strip().removesuffix('.md')
        if not tgt:
            continue
        total += 1
        hit, ambiguous = resolve(tgt)
        if hit is None and Path(tgt).suffix and Path(tgt).name in others:
            continue
        if hit is None:
            dang[tgt] += 1
        else:
            if ambiguous:
                amb[tgt] += 1
            out[p].add(hit)
            inn[hit].add(p)

islands = [p for p in files if not out[p] and not inn[p]]
# Folders whose notes are not yet filed. Override with VAULT_INBOX='Inbox,Triage'.
INBOX = tuple(f for f in os.environ.get('VAULT_INBOX', 'INBOX').split(',') if f)


def bucket(p):
    s = str(p.relative_to(V))
    if any(t in s for t in TERMINAL):
        return 'terminal by design (daily/archive)'
    if any(t in s for t in INBOX):
        return 'inbox - unfiled, wire or file it'
    return 'GENUINE ISLAND'
bc = collections.Counter(bucket(p) for p in islands)

atts = []
for r, d, f in os.walk(V):
    d[:] = [x for x in d if x not in SKIP]
    atts += [Path(r) / n for n in f if not n.endswith('.md')]
alltext = ''.join(p.read_text(errors='ignore') for p in files)
orphan = [a for a in atts if a.name not in alltext]

print(f"[vaultlinks] COVERAGE {len(files)} notes · {total} wikilinks · {len(atts)} attachments · {V}")
print(f"[vaultlinks] DANGLING {sum(dang.values())} ref(s) → {len(dang)} missing target(s)")
for k, v in dang.most_common(10):
    print(f"    x{v:<4} [[{k}]]")
print(f"[vaultlinks] AMBIGUOUS {sum(amb.values())} ref(s) — a bare link whose stem is not unique resolves by coin flip")
for k, v in amb.most_common(5):
    print(f"    x{v:<4} [[{k}]] → {len(stems[k.split('/')[-1]])} candidates")
print(f"[vaultlinks] ISLANDS {len(islands)} of {len(files)}, classified BEFORE any wiring:")
for k, v in bc.most_common():
    print(f"    {v:5}  {k}")
print(f"[vaultlinks] UNREFERENCED ATTACHMENTS {len(orphan)} of {len(atts)}")
print("""[vaultlinks] BLIND SPOTS, printed every run:
    Resolution is Obsidian's documented rule, NOT its index — a plugin-created
      alias or a Bases/Dataview-generated link is invisible here.
    Attachment use is matched by FILENAME in note text; a file referenced only
      by a generated gallery or an absolute path reads as unreferenced.
    An island is not a defect: daily notes and archives are terminal BY DESIGN,
      which is why they are bucketed rather than counted.
    A dangling link is HISTORY. The practice is to mark it *(GONE <date>)*,
      never to delete it — chasing the path is the fault, not the record.""")
