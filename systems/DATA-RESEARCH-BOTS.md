# Data, Research, Bots, and Agents

This subsystem connects research/data acquisition to executable software while preserving the repository's bounded and auditable design.

## Research pipeline

```text
question
  ↓
source discovery
  ↓
source quality filter
  ↓
extraction
  ↓
normalization
  ↓
provenance
  ↓
structured dataset
  ↓
analysis
  ↓
model/agent
  ↓
action or report
```

## Source discipline

Prefer:
- official docs
- primary data
- first-party APIs
- research papers
- source repositories
- dated releases

Record:
- URL/source
- access date
- extraction method
- version/date of source
- transformations
- assumptions

## Data ingestion bounds

Every collector should specify:
- maximum pages
- maximum records
- maximum bytes
- request timeout
- retry budget
- rate limit
- concurrency limit
- deduplication key
- storage retention

## Bots

A bot should have an explicit state machine.

```text
DISCOVER -> VALIDATE -> PLAN -> ACT -> VERIFY -> RECORD
                         |
                      BLOCK/ASK
```

A bot should not decide that a failed verification means it can simply continue with a second uncontrolled attempt.

## Agent loops

Use budgets:
- iterations
- tool calls
- runtime
- cost/tokens
- network calls
- files changed
- bytes written
- parallel tasks

## Research/data package families

Useful classes include HTTP clients, parsers, schema validators, dataframe engines, Arrow/columnar formats, queues, caches, vector databases, SQL clients, and observability libraries.

The package catalog should classify these by purpose instead of popularity.

## What enforces this now

`atlas.yaml` stopped being silent about knowledge, because the default otherwise applies:
everything becomes a document, everything gets embedded, and a question with an exact answer is
served by similarity. That never produces a visibly wrong answer — it produces a plausible one.

- **`data_classes`** — structured, semi-structured and unstructured, each naming how it is
  retrieved AND the way it fails. ABSENT IS NOT ZERO for the first; a field that moved rather than
  vanished for the second; a chunk ending mid-function for the third.
- **`knowledge_layers`** — what each layer must NEVER hold. The defect is always a volatile fact
  in the layer that cannot be updated, and its signature is that nothing in the output looks wrong.
- **`retrieval_policy`** — the defaults that would otherwise win are named as forbidden:
  fixed-length chunking, modification-time invalidation, a dense-only index.
- **`scripts/atlasindex.py`** implements it: declared boundaries only, content-checksum
  invalidation, two search arms that disagree on purpose, and every hit carrying the path, the
  line range and the checksum it was read at.
- **`retrieval_change`** is a change class, because a broken chunk boundary, an index invalidated
  by mtime and an uncited answer all pass a formatter, a typechecker and a green unit suite.
