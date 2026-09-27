#!/usr/bin/env node
// heavyidle — FAILS on the shape: a multi-GB artefact nothing has touched.
//
// WHY THIS EXISTS: a sweep at contract 3.23.1 found 19 GB of idle heavy blobs that had
// accrued silently — a 9.9 GB cowork VM image untouched for 2 days but sized for
// ever, a 1.3 GB git clone of a system CLAUDE.md declares STOPPED, and two ollama
// fine-tunes referenced by zero code paths. None of it was broken; nothing
// reported it; macOS Settings called all of it "Documents". A store with no
// declared bound grows for ever, and the bound must be in BYTES, never in count.
//
// THE BOUND IS IN BYTES AND THE WINDOW IS IN DAYS. Both are declared here, both
// are printed every run, and COVERAGE is printed beside the finding count —
// because flagging 0 of 0 and 0 of 400 print the same "0".
//
// Exit code IS the verdict: 0 clean, 1 findings, 2 a root could not be read.

import { readdirSync, statSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { execFileSync } from 'node:child_process';

const HOME = homedir();
const BYTES = Number(process.env.HEAVYIDLE_BYTES ?? 2 * 1024 ** 3);  // 2 GiB
const DAYS  = Number(process.env.HEAVYIDLE_DAYS  ?? 30);
const NOW = Date.now();

// Each root names WHY it is watched. A root added without a reason is noise.
const ROOTS = [
  { path: join(HOME, 'Downloads'),  depth: 2, why: 'downloads are the classic forgotten multi-GB blob' },
  { path: join(HOME, 'Library', 'Application Support'), depth: 2, why: 'app state blobs — VM images, Electron caches' },
  { path: join(HOME, 'Library', 'Caches'), depth: 1, why: 'regenerable, but unbounded without a writer-side cap' },
  { path: join(HOME, '.ollama', 'models'), depth: 1, why: 'model blobs; apparent size overstates, layers are shared' },
  { path: HOME, depth: 1, why: 'home-root dotdirs — a stopped agent leaves its whole tree behind' },
  { path: join(HOME, 'Projects'), depth: 2, why: 'build artefacts and vendored deps' },
];

// Exemptions carry their reason INLINE or they are a snooze button.
const EXEMPT = [
  { re: /\/Library\/Application Support\/(Claude|Google|Cursor)$/, why: 'live app state for a running app — reclaim is a re-download, not a saving' },
  { re: /\/Projects\/[^/]*ACTIVE[^/]*$/, why: "a project the owner declares active — name your own here" },
  { re: /\/\.ollama\/models\/blobs$/, why: 'blob store is bounded by `ollama list`, not by this guard' },
  { re: /\/(homebrew|\.nvm|\.pyenv|\.rustup|\.cargo|miniconda|go)$/, why: 'toolchain root — removal breaks the shell, not a cleanup' },
];

const findings = [];
let scannedItems = 0, scannedBytes = 0, unreadable = [];

// du -sk is the identity for size on APFS: it reports ALLOCATED blocks, so it is
// correct for sparse images and for ollama's shared layers, where an apparent
// size (stat %z, `ollama list`) overstates. Measured contract 3.23.1: two models
// listed at 7.9 GB freed 3.7 GB.
function allocatedKB(p) {
  try { return Number(execFileSync('du', ['-sk', p], { stdio: ['ignore','pipe','ignore'] })
    .toString().split(/\s+/)[0]); } catch { return null; }
}

function lastTouched(p) {
  // A noatime mount exists on this machine, so atime can be a floor rather than
  // a fact. Take the NEWER of atime/mtime: it can only make the guard more
  // conservative — it never invents staleness.
  try { const s = statSync(p); return Math.max(s.atimeMs, s.mtimeMs); } catch { return NOW; }
}

for (const root of ROOTS) {
  if (!existsSync(root.path)) { unreadable.push(`${root.path} (absent)`); continue; }
  let entries;
  try { entries = readdirSync(root.path, { withFileTypes: true }); }
  catch (e) { unreadable.push(`${root.path} (${e.code})`); continue; }
  for (const e of entries) {
    if (e.name.startsWith('.') && root.path === HOME && !e.isDirectory()) continue;
    const p = join(root.path, e.name);
    const ex = EXEMPT.find(x => x.re.test(p));
    scannedItems++;
    const kb = allocatedKB(p);
    if (kb === null) { unreadable.push(`${p} (unreadable)`); continue; }
    scannedBytes += kb * 1024;
    if (ex) continue;
    if (kb * 1024 < BYTES) continue;
    const ageDays = (NOW - lastTouched(p)) / 86400000;
    if (ageDays < DAYS) continue;
    findings.push({ p, kb, size: kb >= 1048576 ? `${(kb/1048576).toFixed(1)} GiB` : `${Math.round(kb/1024)} MiB`, age: Math.round(ageDays) });
  }
}

const GB = b => (b / 1024 ** 3).toFixed(1);
console.log(`[heavyidle] bound ${GB(BYTES)} GiB · window ${DAYS}d · ${ROOTS.length} roots`);
console.log(`[heavyidle] COVERAGE ${scannedItems} item(s), ${GB(scannedBytes)} GiB measured by du -sk (allocated, not apparent)`);
for (const f of findings.sort((a, b) => b.kb - a.kb))
  console.log(`  IDLE-HEAVY  ${f.size}  untouched ${f.age}d  ${f.p.replace(HOME, '~')}`);
if (unreadable.length) console.log(`[heavyidle] ${unreadable.length} path(s) not measured: ${unreadable.slice(0,3).join(', ')}`);

// Printed EVERY run so a clean pass is never read as more than it is.
console.log(`[heavyidle] BLIND SPOTS: Full Disk Access is off, so protected trees are invisible.
  A noatime mount exists — "untouched" is a FLOOR, a file may be idle longer than shown.
  Depth is capped per root, so a heavy blob nested deeper is NOT seen.
  This measures IDLE, never UNREFERENCED: only code search proves nothing calls it.
  ${EXEMPT.length} exemption(s) active, each carrying its reason inline.`);
console.log(findings.length
  ? `[heavyidle] FAIL — ${findings.length} idle heavy artefact(s), ${GB(findings.reduce((s,f)=>s+f.kb*1024,0))} GiB reclaimable.`
  : `[heavyidle] PASS — 0 of ${scannedItems} item(s) over ${GB(BYTES)} GiB and idle ${DAYS}d.`);
process.exit(unreadable.some(u => u.includes('EACCES')) ? 2 : findings.length ? 1 : 0);
