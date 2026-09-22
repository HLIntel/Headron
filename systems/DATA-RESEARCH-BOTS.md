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