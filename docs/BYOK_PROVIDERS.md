# BYOK Provider Presets

PaperMemory's first BYOK generation path uses an OpenAI-compatible Chat Completions adapter. The API gateway sends requests to:

```text
{base_url.rstrip("/")}/chat/completions
```

Choose a provider preset in the setup wizard or settings panel, then keep the API key in the browser session. Do not commit real API keys to `.env`, docs, screenshots, or test fixtures.

Last checked: 2026-05-19.

| Provider | Base URL | Default model | Image context | Notes |
| --- | --- | --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` | Supported with vision-capable OpenAI models | Standard OpenAI Chat Completions path. |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash` | Supported with multimodal Gemini models | Official Gemini OpenAI compatibility endpoint. |
| DeepSeek | `https://api.deepseek.com` | `deepseek-v4-flash` | Not assumed | Uses current DeepSeek v4 examples. Avoid defaulting new configs to `deepseek-chat` or `deepseek-reasoner` because those aliases are scheduled for deprecation on 2026-07-24. |
| Kimi / Moonshot | `https://api.moonshot.cn/v1` | `kimi-k2.6` | Model-dependent | Moonshot SDK base URL maps to `/v1/chat/completions` after PaperMemory appends `/chat/completions`. New configurations default to `kimi-k2.6`, not the older K2 preview series. |
| MiniMax | `https://api.minimax.io/v1` | `MiniMax-M2.7` | Not assumed | MiniMax documents the OpenAI-compatible text chat endpoint at `/v1/chat/completions`; PaperMemory stores the base URL only. |
| OpenRouter | `https://openrouter.ai/api/v1` | `openai/gpt-4o` | Model-dependent | Router preset for many OpenAI-compatible models through one key. |
| MiMo via OpenRouter | `https://openrouter.ai/api/v1` | `xiaomi/mimo-v2.5` | Model-dependent | Public stable MiMo access is represented through OpenRouter. This preset does not claim a Xiaomi direct endpoint. |
| Together AI | `https://api.together.xyz/v1` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Model-dependent | Hosted open models behind an OpenAI-compatible API. |
| Alibaba DashScope / Qwen | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` | Supported with VL models | DashScope compatible mode for Qwen models. |
| Mistral | `https://api.mistral.ai/v1` | `mistral-large-latest` | Model-dependent | OpenAI-compatible chat endpoint; choose a model that matches your evidence mode. |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | Model-dependent | OpenAI-compatible low-latency hosted models. |
| xAI | `https://api.x.ai/v1` | `grok-4.3` | Model-dependent | OpenAI-compatible xAI endpoint. Choose a vision-capable Grok model when attaching page images. |
| Custom | `http://localhost:8001/v1` | `local-vlm` | Model-dependent | Any local or hosted OpenAI-compatible server that exposes `/chat/completions`. |

## Image Context Guidance

When `PAPERMEMORY_BYOK_ENABLE_IMAGE_CONTEXT=true`, PaperMemory attaches retrieved page images as OpenAI-style `image_url` data URLs. Use this only with a provider and model that accepts image inputs. For text-only models, leave image context disabled and rely on the evidence prompt plus text snippets.

## Backend Scope

These presets are UI defaults for the existing OpenAI-compatible adapter. Anthropic-native APIs are intentionally excluded because they use a different protocol shape and are not covered by the current gateway.
