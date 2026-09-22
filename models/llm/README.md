# LLM Provider Layer

This directory is the provider and endpoint configuration layer. Actual credentials do not belong in Git.

## Secret rule
Never commit API keys, OAuth tokens, bearer tokens, private keys, session cookies, or provider credentials.
Use environment variables, OS credential stores, CI secrets, or a dedicated secret manager.

## Provider classes
| Provider | Typical role |
|---|---|
| NVIDIA NIM | NVIDIA-hosted/self-hosted inference endpoints |
| OpenRouter | multi-provider gateway |
| Cloudflare Workers AI | edge/managed inference |
| OpenAI | direct model/API access |
| Anthropic | direct Claude API |
| Google | Gemini APIs |
| Mistral | direct model/API access |
| Groq | low-latency inference |
| Together | hosted open-model inference |
| Fireworks | hosted open-model inference |
| Cerebras | high-throughput inference |
| Cohere | language/retrieval workloads |
| Ollama | local model serving |
| vLLM | self-hosted OpenAI-compatible serving |
| LM Studio | local model serving |

## Normalized provider record
```yaml
provider: openrouter
model: provider/model-id
base_url: https://example.invalid
auth_env: OPENROUTER_API_KEY
protocol: openai-compatible
timeout_s: 60
max_retries: 2
max_output_tokens: 4096
```

Keep provider URLs/model IDs in one registry rather than scattering them through code.

## Fallback
`primary -> finite retry -> fallback -> stop`

Provider models, pricing, context limits, and endpoints change; verify current values before relying on them.

## References
- NVIDIA NIM: https://docs.nvidia.com/nim/
- OpenRouter: https://openrouter.ai/docs
- Cloudflare Workers AI: https://developers.cloudflare.com/workers-ai/
- OpenAI: https://platform.openai.com/docs
- Anthropic: https://docs.anthropic.com/
- Google AI: https://ai.google.dev/
- Mistral: https://docs.mistral.ai/
- Ollama: https://docs.ollama.com/
- vLLM: https://docs.vllm.ai/