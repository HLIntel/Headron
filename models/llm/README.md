# LLM Provider Layer

Provider credentials and endpoint metadata live here conceptually; actual credentials never belong in Git.

## Providers
NVIDIA NIM, OpenRouter, Cloudflare Workers AI, OpenAI, Anthropic, Google, Mistral, Groq, Together, Fireworks, Cerebras, Cohere, Ollama, vLLM, LM Studio.

## Provider record
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

## Secret rule
Only environment-variable names or secret-manager references belong in the repository.

## Endpoint routing
Keep model IDs/base URLs in one registry. Verify current provider capabilities before use.

## Fallback
Finite retry -> finite fallback -> stop.

Official references: https://docs.nvidia.com/nim/ , https://openrouter.ai/docs , https://developers.cloudflare.com/workers-ai/ , https://platform.openai.com/docs , https://docs.anthropic.com/