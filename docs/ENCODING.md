# Encoding and compression — what Thea adopts, measures first, or refuses

The goal is one thing: **an AI given Thea reads less and does the task better.** Every technique
below is judged against that, and against one constraint that is not negotiable: **a compressed form
must expand, deterministically, back to its canonical source, and that expansion is checked.**
A representation nobody can expand and check is a second copy that drifts, or a hiding place.

## Adopt — already in the tree, extend deliberately

| technique | where it lives now | the rule it follows |
|---|---|---|
| **Reference layer (IDs instead of repeated prose)** | failure modes, gates, change classes, processes, intents and instruments are ids in `atlas.yaml`; documents cite the id | one declaration, many pointers — `one_source_of_truth` |
| **Expansion layer** | `atlas route`, `atlas gate`, `atlas plan`, `atlas why` expand an id or a path into the full instruction | an agent expands only what its task names — `context_is_progressively_disclosed` |
| **Validation layer** | every generated block and file is re-rendered from its declaration and compared on each build | drift fails the build — `atlas_consistency` |
| **Semantic compression** | `atlas gate` answers with one command instead of a pack's whole tool list | measured per model: the right answer for a small fraction of the tokens (README) |
| **Domain-specific language** | `atlas.yaml` itself — routes, gates, profiles, `extends`, verbs | a DSL only earns its place with a validator and a planted defect per rule |
| **Abstract syntax trees** | the shape gate compares Python functions structurally, not as text | structure is compared as structure — duplicate shapes are refused |
| **Compositional records** | change classes `extends: [source_change]`; runners compose steps | composition is resolved by one function, and tested |

**Next, in this order:** a single `expand <id>` answer across every id namespace, and a guard that
every id a document cites resolves. That turns the reference layer from a convention into a contract.

## Measure first — plausible, and unproven here

- **Symbolic or glyph shorthand ("AI braille").** A symbol saves tokens only if the target model's
  tokenizer spends fewer tokens on it *and* the model reads it as reliably as the words. Rare glyphs
  often cost *more* tokens than the words they replace, and they cost accuracy on models that were
  not trained on them. Gate: an A/B on real prompts, per model, printing tokens *and* accuracy.
- **Token-level compression of prompts** (dropping stop-words, abbreviations). It sometimes trims
  tokens and always risks meaning. Same gate: no adoption without accuracy held on the same questions.
- **Layered or multi-level encodings.** Each layer is another expansion to validate. Adopt a layer
  only when it removes more tokens than its own decoder instructions cost, measured.

## Refuse — and guard against

- **Zero-width characters, Unicode tag characters, bidirectional overrides, steganography, any data
  hidden in text.** This tree is handed to models whole. An invisible character can carry an
  instruction no reviewer sees, or make a reviewer see something other than what runs
  ([CVE-2021-42574](https://nvd.nist.gov/vuln/detail/CVE-2021-42574), "Trojan Source"). As a
  compression channel it saves nothing a reference id does not, and it cannot be reviewed.
  **Enforced:** `atlas.py check` fails on any invisible code point in a tracked text file.

## The test every proposal passes before it lands

1. Does it expand back to a canonical source, deterministically?
2. Is that expansion checked on every build?
3. Was it measured to save tokens **without** costing accuracy, on more than one model?
4. Can a human reviewer read what the model reads?

A proposal that fails any one of these is refused, however clever the encoding.
