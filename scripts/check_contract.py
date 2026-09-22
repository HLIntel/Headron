from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(name):
    return (ROOT / name).read_text(encoding='utf-8')

version = read('VERSION').strip()
errors = []

for path in ['MODEL.md', 'README.md', 'ABOUT.md', 'docs/VERSIONING.md', 'atlas.yaml']:
    if version not in read(path):
        errors.append(f'version mismatch: {path} != {version}')

required = [
    'MODEL.md', 'README.md', 'atlas.yaml', 'docs/INDEX.md',
    'docs/LANGUAGE-SPEC.md', 'languages/ATLAS.md',
    'models/README.md', 'integrations/AI-CAPABILITIES.md',
    'patterns/NO-UNBOUNDED.md', 'patterns/ANTI-MUTATION.md',
]

for path in required:
    if not (ROOT / path).exists():
        errors.append(f'missing required path: {path}')

if (ROOT / 'AGENTS.md').exists():
    errors.append('stale root AGENTS.md exists; MODEL.md is canonical')

for alias in ['docs/PYTHON.md', 'docs/RUST.md', 'docs/GO.md', 'docs/TYPESCRIPT.md']:
    p = ROOT / alias
    if not p.is_symlink():
        errors.append(f'expected symlink: {alias}')
    elif not (p.parent / p.readlink()).exists():
        errors.append(f'broken symlink: {alias} -> {p.readlink()}')

atlas = read('atlas.yaml')
for suffix in ['.py', '.rs', '.go', '.ts', '.sql', '.cu', '.lean']:
    if f"  '{suffix}':" not in atlas:
        errors.append(f'artifact route missing: {suffix}')

model = read('MODEL.md')
for adapter in [
    'models/claude/README.md', 'models/cursor/README.md',
    'models/openai/README.md', 'models/opencode/README.md',
    'models/hermes/README.md', 'models/llm/README.md'
]:
    if adapter not in model:
        errors.append(f'model adapter missing from MODEL.md: {adapter}')

if errors:
    print('Code-Development contract check: FAIL')
    print('\n'.join('- ' + e for e in errors))
    sys.exit(1)

print(f'Code-Development contract {version}: OK')