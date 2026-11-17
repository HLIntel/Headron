# Recorded results, per model

Each table is one record, read on its own contract version and task set. Rows are listed
alphabetically, never ranked; a rate is never summed across records. The README carries the totals.

<!-- BEGIN generated: model-details (python scripts/atlas.py index --write) -->
Routing questions (unassisted vs scoped prompt):

| Model | Contract | Unassisted | Scoped | Tokens/question |
| :--- | :--- | :--- | :--- | :--- |
| `claude-cli:haiku` | 3.49.0 | 30/76 | 76/76 | 151 → 62 |
| `claude-cli:opus` | 3.49.0 | 31/76 | 76/76 | 204 → 92 |
| `claude-cli:sonnet` | 3.49.0 | 30/76 | 76/76 | 202 → 92 |
| `cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast` | 2.28.0 | 23/39 | 38/39 | 170 → 94 |
| `cloudflare:@cf/mistralai/mistral-small-3.1-24b-instruct` | 2.28.0 | 24/39 | 38/39 | 143 → 65 |
| `cloudflare:@cf/qwen/qwen2.5-coder-32b-instruct` | 2.28.0 | 29/39 | 38/39 | 164 → 88 |
| `groq:openai/gpt-oss-120b` | 2.28.0 | 30/39 | 38/39 | 205 → 129 |
| `ollama:gemma4:31b-cloud` | 2.28.0 | 29/39 | 39/39 | 150 → 72 |

Task bench (blind vs with Headron, by kind):

| Model | Contract | Kind | Blind | With Headron |
| :--- | :--- | :--- | :--- | :--- |
| `claude-cli:haiku` | 2.29.0 | diagnose | 18/28 | 27/28 |
| `claude-cli:haiku` | 2.29.0 | hygiene | 4/10 | 10/10 |
| `claude-cli:haiku` | 2.29.0 | plan | 0/8 | 8/8 |
| `claude-cli:opus` | 2.29.0 | diagnose | 26/28 | 28/28 |
| `claude-cli:opus` | 2.29.0 | hygiene | 6/10 | 10/10 |
| `claude-cli:opus` | 2.29.0 | plan | 1/8 | 8/8 |
| `claude-cli:sonnet` | 2.29.0 | diagnose | 16/28 | 28/28 |
| `claude-cli:sonnet` | 2.29.0 | hygiene | 6/10 | 10/10 |
| `claude-cli:sonnet` | 2.29.0 | plan | 1/8 | 8/8 |

Free-model screen (paired tasks only; tokens are the lane's whole run):

| Lane | Paired | Blind | With Headron | Tokens blind / Headron |
| :--- | :--- | :--- | :--- | :--- |
| `gemini:models/gemini-3-flash-preview` | 11 | 3 | 3 | 12,352 / 36,916 |
| `gemini:models/gemini-3.1-flash-lite` | 22 | 8 | 22 | 13,378 / 38,231 |
| `gemini:models/gemini-3.1-flash-lite-preview` | 22 | 8 | 22 | 13,378 / 38,231 |
| `gemini:models/gemini-3.5-flash-lite` | 18 | 8 | 16 | 13,378 / 38,231 |
| `gemini:models/gemini-flash-lite-latest` | 18 | 9 | 17 | 13,378 / 38,231 |
| `gemini:models/gemini-robotics-er-2-preview` | 12 | 1 | 6 | 12,798 / 37,183 |
| `groq:allam-2-7b` | 8 | 1 | 2 | 15,149 / 3,320 |
| `groq:openai/gpt-oss-120b` | 13 | 9 | 13 | 5,822 / 36,171 |
| `groq:openai/gpt-oss-20b` | 1 | 0 | 1 | 133 / 29,245 |
| `groq:openai/gpt-oss-safeguard-20b` | 0 | 0 | 0 | 1,476 / no arm |
| `groq:qwen/qwen3.8-27b` | 2 | 2 | 2 | 4,266 / 12,884 |
| `kilo:baidu/ernie-5.5-flash-preview:free` | 3 | 3 | 3 | 4,486 / 34,149 |
| `kilo:cohere/north-mini-code:free` | 0 | 0 | 0 | 114 / 6,963 |
| `kilo:dots-studio/dots-3-note-preview:free` | 0 | 0 | 0 | no arm / 12,895 |
| `kilo:nvidia/nemotron-3-ultra-550b-a55b:free` | 1 | 0 | 1 | 1,761 / 6,840 |
| `kilo:nvidia/nemotron-3.5-super-vl:free` | 0 | 0 | 0 | no arm / 21,796 |
| `kilo:particle-ai/particle-1:free` | 6 | 5 | 6 | 7,581 / 38,439 |
| `openrouter:inclusionai/ling-3.2-flash:free` | 1 | 1 | 1 | 1,499 / 28,438 |

1,937 graded answers across these records (a count, not a score).
<!-- END generated: model-details -->
