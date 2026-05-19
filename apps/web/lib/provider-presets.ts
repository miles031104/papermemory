export type ImageContextSupport = "supported" | "model-dependent" | "not-assumed";

export interface ProviderPreset {
  company: string;
  baseUrl: string;
  model: string;
  note: string;
  supportsImageContext: ImageContextSupport;
  docsUrl: string;
  category: "first-party" | "router" | "hosted-open-models" | "custom";
}

export const providerPresets: ProviderPreset[] = [
  {
    company: "OpenAI",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o",
    note: "OpenAI Chat Completions. Image context works with vision-capable OpenAI models.",
    supportsImageContext: "supported",
    docsUrl: "https://platform.openai.com/docs/api-reference/chat",
    category: "first-party"
  },
  {
    company: "Google Gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
    model: "gemini-2.5-flash",
    note: "Gemini OpenAI compatibility endpoint. Image context is supported by multimodal Gemini models.",
    supportsImageContext: "supported",
    docsUrl: "https://ai.google.dev/gemini-api/docs/openai",
    category: "first-party"
  },
  {
    company: "DeepSeek",
    baseUrl: "https://api.deepseek.com",
    model: "deepseek-v4-flash",
    note: "DeepSeek OpenAI-compatible endpoint. Default uses current v4 examples; older deepseek-chat aliases are not used.",
    supportsImageContext: "not-assumed",
    docsUrl: "https://api-docs.deepseek.com/",
    category: "first-party"
  },
  {
    company: "Kimi / Moonshot",
    baseUrl: "https://api.moonshot.cn/v1",
    model: "kimi-k2.6",
    note: "Moonshot OpenAI-compatible endpoint. New configurations default to kimi-k2.6, not the older K2 preview series.",
    supportsImageContext: "model-dependent",
    docsUrl: "https://platform.moonshot.cn/docs",
    category: "first-party"
  },
  {
    company: "MiniMax",
    baseUrl: "https://api.minimax.io/v1",
    model: "MiniMax-M2.7",
    note: "MiniMax OpenAI-compatible chat completions endpoint. Use text evidence unless the chosen model documents image input.",
    supportsImageContext: "not-assumed",
    docsUrl: "https://platform.minimax.io/docs/api-reference/text-chat-openai",
    category: "first-party"
  },
  {
    company: "OpenRouter",
    baseUrl: "https://openrouter.ai/api/v1",
    model: "openai/gpt-4o",
    note: "Routes to many OpenAI-compatible models through one key. Image context depends on the selected route.",
    supportsImageContext: "model-dependent",
    docsUrl: "https://openrouter.ai/docs",
    category: "router"
  },
  {
    company: "MiMo via OpenRouter",
    baseUrl: "https://openrouter.ai/api/v1",
    model: "xiaomi/mimo-v2.5",
    note: "Public MiMo access preset through OpenRouter, not a claimed Xiaomi direct endpoint.",
    supportsImageContext: "model-dependent",
    docsUrl: "https://openrouter.ai/xiaomi",
    category: "router"
  },
  {
    company: "Together AI",
    baseUrl: "https://api.together.xyz/v1",
    model: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    note: "OpenAI-compatible hosted open models. Image context depends on the selected model.",
    supportsImageContext: "model-dependent",
    docsUrl: "https://docs.together.ai/docs/openai-api-compatibility",
    category: "hosted-open-models"
  },
  {
    company: "Alibaba DashScope / Qwen",
    baseUrl: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    model: "qwen-vl-plus",
    note: "DashScope compatible-mode endpoint for Qwen. Image context works with VL models.",
    supportsImageContext: "supported",
    docsUrl: "https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope",
    category: "first-party"
  },
  {
    company: "Mistral",
    baseUrl: "https://api.mistral.ai/v1",
    model: "mistral-large-latest",
    note: "Mistral OpenAI-compatible chat endpoint. Image context depends on the selected model.",
    supportsImageContext: "model-dependent",
    docsUrl: "https://docs.mistral.ai/api/",
    category: "first-party"
  },
  {
    company: "Groq",
    baseUrl: "https://api.groq.com/openai/v1",
    model: "llama-3.3-70b-versatile",
    note: "Groq OpenAI-compatible endpoint. Image context depends on the selected model.",
    supportsImageContext: "model-dependent",
    docsUrl: "https://console.groq.com/docs/openai",
    category: "hosted-open-models"
  },
  {
    company: "xAI",
    baseUrl: "https://api.x.ai/v1",
    model: "grok-4.3",
    note: "xAI OpenAI-compatible endpoint. Image context is model-dependent; choose a vision-capable Grok model when attaching page images.",
    supportsImageContext: "model-dependent",
    docsUrl: "https://docs.x.ai/docs/guides/chat-completions",
    category: "first-party"
  },
  {
    company: "Custom",
    baseUrl: "http://localhost:8001/v1",
    model: "local-vlm",
    note: "Any local or hosted OpenAI-compatible server that exposes /chat/completions.",
    supportsImageContext: "model-dependent",
    docsUrl: "docs/BYOK_PROVIDERS.md",
    category: "custom"
  }
];

export function findProviderPreset(company: string): ProviderPreset | undefined {
  return providerPresets.find((preset) => preset.company === company);
}
