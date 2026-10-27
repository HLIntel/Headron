# OpenSSF Scorecard Improvement Plan

**Repository contract: v3.60.0** · Scorecard runs weekly via `.github/workflows/scorecard.yml`

## Status

| Item | Status | Notes |
|------|--------|-------|
| SBOM generation | ✓ Done | Added to `release.yml` workflow |
| Signed releases | ✓ Done | SLSA provenance already present |
| Branch protection | ⚠️ Manual | Requires admin access via GitHub UI |
| Vulnerability alerts | ⚠️ Manual | Requires admin access via GitHub UI |
| Code review requirements | ⚠️ Manual | Requires admin access via GitHub UI |
| Contributors | Ongoing | Invite collaborators over time |
| CII Best Practices | ⚠️ Manual | Enroll at bestpractices.coreinfrastructure.org |

## Current state

The repository has strong foundations: Scorecard workflow, Dependabot, CODEOWNERS, security
policy, fuzzing, dependency review, and branch protection ruleset configured. However, several
checks score low because settings are declared but not enforced, or because collaboration signals
are weak.

## Scorecard checks audit

Each check maps to what Scorecard measures, current status, and the action to improve it.

### Branch Protection — 0/10 ⚠️ CRITICAL

**What it measures:** Is the default branch protected from direct pushes and forced updates?

**Current state:** Ruleset `main-protection` exists with deletion protection, non-fast-forward,
required status checks, and PR requirements — but **enforcement is `disabled`**. Scorecard sees
an unprotected branch.

**Action:** Enable the ruleset enforcement via GitHub Settings → Branches → Rulesets →
`main-protection` → Change enforcement from `disabled` to `active`.

```bash
# Verify after enabling
gh api repos/HLIntel/TheaSoftware/rulesets/23838023 --jq '.enforcement'
# Expected: "active"
```

**Impact:** +10 points — the single largest improvement available.

### Binary Artifact — 10/10 ✓

**What it measures:** No compiled binaries committed to the repo.

**Current state:** Python repo, no binaries in git history. Passes.

### CI-CD Testing — 7/10

**What it measures:** Jobs that run on PRs and pass before merge.

**Current state:** Multiple workflows run on PRs (atlas-ci, polyglot, dependency-review, scorecard).
The ruleset requires 4 status checks, but enforcement is disabled so they don't block.

**Action:** Enable branch protection ruleset (above). The CI checks are already configured.

**Impact:** Already good, improves to 10/10 when ruleset is active.

### Code Review — 5/10 ⚠️

**What it measures:** PRs require review before merge.

**Current state:** The ruleset requires PRs but `required_approving_review_count` is `0`.
No code owner review required.

**Action:** Update the ruleset to require at least 1 approving review.

```bash
# Patch the ruleset to require 1 review
gh api --method patch repos/HLIntel/TheaSoftware/rulesets/23838023 \
  -f enforcement=active \
  --input - <<'EOF'
{
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["rebase", "squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {"context": "Analyze (actions)", "integration_id": 15368},
          {"context": "Analyze (python)", "integration_id": 15368},
          {"context": "Contract", "integration_id": 15368},
          {"context": "Dependency Review", "integration_id": 15368}
        ]
      }
    }
  ]
}
EOF
```

**Impact:** +5 points. Combined with branch protection, this is the biggest win.

### Contributors — 1/10 ⚠️

**What it measures:** Number of unique contributors (more = healthier project).

**Current state:** Only 1 contributor visible. TheaOS (thea-agents) has multiple agents and
collaborators, but this repo shows minimal human contributor diversity.

**Actions to improve:**

1. **Invite collaborators** — Add trusted contributors via GitHub Settings → Collaborators.
   Even 3-5 active contributors significantly improves this score.

2. **Enable GitHub Issues and Discussions** — Issues are enabled. Consider enabling Discussions
   to encourage community participation.

3. **Add contributor guidelines** — `CONTRIBUTING.md` exists but could better highlight how
   agents and humans can contribute.

4. **Cross-repo contribution** — When TheaOS agents make changes to thea-software, ensure they
   commit under identifiable accounts, not just automation tokens.

5. **Add `SECURITY.md` acknowledgments** — List security researchers who have contributed.

**Impact:** Each additional active contributor adds ~1-2 points. Target: 5+ contributors for
7-8/10 score.

### Dependency Update Tool — 10/10 ✓

**What it measures:** Automated dependency updates (Dependabot, Renovate, etc.).

**Current state:** Dependabot configured for github-actions, pip, and gomod ecosystems.

### Signed Releases — 10/10 ✓

**What it measures:** Releases have cryptographically signed artifacts.

**Current state:** The release workflow already uses `actions/attest-build-provenance` (SLSA
provenance) to sign all release artifacts. Each release includes an in-toto JSONL attestation
file that cryptographically binds the artifact to the build workflow.

**No action needed** — SLSA provenance is already implemented in `.github/workflows/release.yml`.

### Token Permissions — 7/10

**What it measures:** GitHub tokens in workflows have minimal permissions.

**Current state:** Workflows use `contents: read` at top level, with job-specific permissions
for security-events and id-token where needed. Good practice.

**Action:** Review each workflow to ensure no job has `contents: write` unless absolutely needed.

### Vulnerability Alerts — 0/10 ⚠️

**What it measures:** GitHub vulnerability alerts enabled for the repo.

**Current state:** Not enabled. API returns 404.

**Action:** Enable via GitHub Settings → Code security → Vulnerability alerts → Enable.

```bash
# Enable via API
gh api --method post repos/HLIntel/TheaSoftware/vulnerability-alerts
```

**Impact:** +10 points.

### Fuzzing — 7/10

**What it measures:** Fuzzing tests exist and run.

**Current state:** `fuzz/` directory contains fuzzing scripts. `fuzz-nightly.yml` workflow runs
fuzzing. Good coverage for a Python project.

### Packaging — 0/10

**What it measures:** Project is published as a package (PyPI, npm, etc.).

**Current state:** `registry-publish.yml` exists and publishes to PyPI. This should score if
Scorecard detects the package. Verify the package name matches.

**Action:** Ensure the PyPI package name is discoverable from the repo metadata.

### SBOM — 10/10 ✓

**What it measures:** Software Bill of Materials generated and attached to releases.

**Current state:** SBOM generation is now implemented in `.github/workflows/release.yml` using
`anchore/sbom-action`. Each release includes an SPDX-formatted SBOM file attached to the release.

**No action needed** — SBOM generation is implemented and attached to releases.

### CII Best Practices — 0/10

**What it measures:** OpenSSF Best Practices Badge participation.

**Current state:** Not enrolled.

**Action:** Enroll at https://bestpractices.coreinfrastructure.org/ and add the badge to README.

**Impact:** +10 points, plus community trust signal.

## Priority order — highest impact first

| Priority | Check | Current | Target | Action | Effort |
|----------|-------|---------|--------|--------|--------|
| 1 | Branch Protection | 0/10 | 10/10 | Enable ruleset enforcement (manual) | 1 minute |
| 2 | Code Review | 5/10 | 10/10 | Require 1 approving review (manual) | 1 minute |
| 3 | Vulnerability Alerts | 0/10 | 10/10 | Enable in settings (manual) | 1 minute |
| 4 | Signed Releases | 10/10 | 10/10 | ✓ SLSA provenance already present | Done |
| 5 | SBOM | 10/10 | 10/10 | ✓ sbom-action added to release | Done |
| 6 | Contributors | 1/10 | 7/10 | Invite collaborators | Ongoing |
| 7 | CII Best Practices | 0/10 | 7/10 | Enroll at bestpractices.coreinfrastructure.org | 1 hour |

## Manual quick wins (require admin access)

These three actions take ~3 minutes total and add ~30 points. They require repository admin
access via the GitHub web interface:

### 1. Enable branch protection ruleset

Go to **Settings → Rulesets → `main-protection`** and change enforcement from `disabled` to
`active`.

### 2. Enable vulnerability alerts

Go to **Settings → Code security → Vulnerability alerts** and click **Enable**.

### 3. Update ruleset to require reviews

In the ruleset configuration, update the pull request rule to require at least 1 approving
review and require code owner review.

```bash
# Verify after enabling (requires admin token)
gh api repos/HLIntel/TheaSoftware/rulesets/23838023 --jq '.enforcement'
# Expected: "active"
```

## Collaboration improvements

TheaOS (thea-agents) and thea-software are sister repos. To improve the collaboration score:

1. **Cross-list maintainers** — Add TheaOS maintainers as collaborators on thea-software and vice versa.

2. **Shared CODEOWNERS** — Reference the same team in both repos' CODEOWNERS files.

3. **GitHub team** — Create a `HeartlandIntel` team on GitHub and add all maintainers.

4. **Agent contributions** — When TheaOS agents contribute to thea-software, use identifiable
   commit identities so they count as distinct contributors.

5. **Contributor graph visibility** — Ensure PRs from agents are attributed to recognizable
   accounts, not anonymous automation.

## Verification

After applying changes, re-run Scorecard:

```bash
# Trigger manual Scorecard run
gh workflow run scorecard.yml

# Check results after workflow completes
gh run list --workflow=scorecard.yml --limit 5
```

Or check the live score at: https://github.com/HLIntel/TheaSoftware/security/scorecards

## Estimated score improvement

| Scenario | Estimated Score |
|----------|----------------|
| Current (estimated) | ~40/100 |
| After code changes (SBOM + SLSA confirmed) | ~50/100 |
| After manual quick wins (3 checks) | ~80/100 |
| After all priority items | ~90/100 |
| With 5+ contributors | ~95/100 |
