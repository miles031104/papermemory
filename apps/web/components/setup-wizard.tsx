import { findProviderPreset, providerPresets } from "@/lib/provider-presets";
import type { InstallMode, InstallSettings, ModelSettings } from "@/lib/types";

interface SetupWizardProps {
  settings: InstallSettings;
  onChange: (settings: InstallSettings) => void;
  onApplyModelSettings: (settings: ModelSettings) => void;
}

const modeCopy: Record<InstallMode, { title: string; detail: string }> = {
  demo: {
    title: "Demo stub",
    detail: "No model download. Uses 8-dimensional deterministic retrieval for UI and API testing."
  },
  "local-visrag": {
    title: "Local VisRAG-Ret",
    detail:
      "Downloads openbmb/VisRAG-Ret locally, uses 2304-dimensional page embeddings, and needs a fresh Qdrant collection."
  },
  custom: {
    title: "Custom",
    detail: "Manually choose backend, vector size, model repo, device, and provider endpoint."
  }
};

function applyMode(settings: InstallSettings, mode: InstallMode): InstallSettings {
  if (mode === "demo") {
    return {
      ...settings,
      mode,
      visragBackend: "stub",
      qdrantVectorSize: 8,
      trustRemoteCode: false
    };
  }

  if (mode === "local-visrag") {
    return {
      ...settings,
      mode,
      visragBackend: "transformers",
      qdrantVectorSize: 2304,
      trustRemoteCode: true
    };
  }

  return { ...settings, mode };
}

function envPreview(settings: InstallSettings) {
  const lines = [
    `NEXT_PUBLIC_API_BASE_URL=${settings.apiBaseUrl}`,
    `PAPERMEMORY_STORAGE_ROOT=${settings.storageRoot}`,
    `PAPERMEMORY_QDRANT_URL=${settings.qdrantUrl}`,
    `PAPERMEMORY_QDRANT_VECTOR_SIZE=${settings.qdrantVectorSize}`,
    `PAPERMEMORY_VISRAG_BACKEND=${settings.visragBackend}`,
    `PAPERMEMORY_VISRAG_MODEL_NAME=${settings.visragModel}`,
    `PAPERMEMORY_VISRAG_DEVICE=${settings.visragDevice}`,
    `PAPERMEMORY_VISRAG_DTYPE=${settings.visragDtype}`,
    `PAPERMEMORY_VISRAG_TRUST_REMOTE_CODE=${settings.trustRemoteCode ? "true" : "false"}`,
    `PAPERMEMORY_BYOK_ENABLE_IMAGE_CONTEXT=${settings.useMultimodalContext ? "true" : "false"}`,
    `PAPERMEMORY_BYOK_MAX_EVIDENCE_IMAGES=${settings.maxEvidenceImages}`,
    `PAPERMEMORY_BYOK_MAX_IMAGE_BYTES=2097152`,
    `PAPERMEMORY_BYOK_BASE_URL=${settings.providerBaseUrl}`,
    `PAPERMEMORY_BYOK_MODEL=${settings.providerModel}`
  ];

  if (settings.hfToken.trim()) {
    lines.push("HF_TOKEN=<provided in this setup session>");
  }

  return lines.join("\n");
}

export function SetupWizard({ settings, onChange, onApplyModelSettings }: SetupWizardProps) {
  const update = (patch: Partial<InstallSettings>) => onChange({ ...settings, ...patch });
  const activePreset = findProviderPreset(settings.providerCompany);
  const customPreset = findProviderPreset("Custom") ?? providerPresets[0];
  const selectedPreset = activePreset ?? customPreset;
  const showCompanyLabelInput = !activePreset || activePreset.company === "Custom";
  const isRealVisrag = settings.visragBackend === "transformers";
  const hasVisragDimensionMismatch = isRealVisrag && settings.qdrantVectorSize !== 2304;

  const applyProvider = (company: string) => {
    const preset = findProviderPreset(company);
    if (!preset) {
      return;
    }
    update({
      providerCompany: preset.company,
      providerBaseUrl: preset.baseUrl,
      providerModel: preset.model
    });
  };

  const applyToChat = () => {
    onApplyModelSettings({
      provider: "openai-compatible",
      providerCompany: settings.providerCompany,
      baseUrl: settings.providerBaseUrl,
      model: settings.providerModel,
      apiKey: settings.providerApiKey,
      temperature: 0.2,
      retrievalTopK: 5,
      requireEvidence: true,
      useMultimodalContext: settings.useMultimodalContext,
      maxEvidenceImages: settings.maxEvidenceImages
    });
  };

  return (
    <section className="panel setup-panel" aria-labelledby="setup-title">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Install setup</p>
          <h2 id="setup-title">Configure local PaperMemory</h2>
          <p>Choose retrieval mode, Hugging Face access, local services, and BYOK generation.</p>
        </div>
        <button className="button button--primary" type="button" onClick={applyToChat}>
          Apply to chat
        </button>
      </div>

      <div className="setup-grid">
        <div className="setup-section">
          <h3>1. Mode</h3>
          <div className="segmented" role="group" aria-label="Installation mode">
            {(["demo", "local-visrag", "custom"] as InstallMode[]).map((mode) => (
              <button
                className={`segment ${settings.mode === mode ? "segment--active" : ""}`}
                key={mode}
                type="button"
                onClick={() => onChange(applyMode(settings, mode))}
              >
                {modeCopy[mode].title}
              </button>
            ))}
          </div>
          <p className="small-muted">{modeCopy[settings.mode].detail}</p>
          {isRealVisrag ? (
            <p className="inline-alert inline-alert--warning">
              Real VisRAG-Ret uses 2304-dimensional vectors. Qdrant collection dimensions are fixed, so
              switching from the 8D demo stub requires recreating the collection and reindexing PDFs.
            </p>
          ) : null}
        </div>

        <div className="setup-section">
          <h3>2. VisRAG / Hugging Face</h3>
          <div className="field-grid setup-field-grid">
            <div className="field">
              <label htmlFor="setup-hf-token">HF token</label>
              <input
                id="setup-hf-token"
                type="password"
                value={settings.hfToken}
                onChange={(event) => update({ hfToken: event.target.value })}
                placeholder="Optional unless HF access requires it"
                autoComplete="off"
              />
            </div>
            <div className="field">
              <label htmlFor="setup-visrag-model">Model repo</label>
              <input
                id="setup-visrag-model"
                type="text"
                value={settings.visragModel}
                onChange={(event) => update({ visragModel: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="setup-visrag-backend">Retriever backend</label>
              <select
                id="setup-visrag-backend"
                value={settings.visragBackend}
                onChange={(event) =>
                  update({
                    visragBackend: event.target.value as InstallSettings["visragBackend"]
                  })
                }
              >
                <option value="stub">Stub</option>
                <option value="transformers">Transformers</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="setup-vector-size">Vector size</label>
              <input
                id="setup-vector-size"
                type="number"
                min="1"
                value={settings.qdrantVectorSize}
                onChange={(event) => update({ qdrantVectorSize: Number(event.target.value) })}
              />
            </div>
            <div className="field">
              <label htmlFor="setup-device">Device</label>
              <select
                id="setup-device"
                value={settings.visragDevice}
                onChange={(event) =>
                  update({ visragDevice: event.target.value as InstallSettings["visragDevice"] })
                }
              >
                <option value="auto">Auto</option>
                <option value="cuda">CUDA</option>
                <option value="cpu">CPU</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="setup-dtype">Dtype</label>
              <select
                id="setup-dtype"
                value={settings.visragDtype}
                onChange={(event) =>
                  update({ visragDtype: event.target.value as InstallSettings["visragDtype"] })
                }
              >
                <option value="auto">Auto</option>
                <option value="bfloat16">bfloat16</option>
                <option value="float16">float16</option>
                <option value="float32">float32</option>
              </select>
            </div>
          </div>
          <div className="toggle setup-toggle">
            <label htmlFor="setup-trust-remote">Allow HF custom model code</label>
            <input
              id="setup-trust-remote"
              type="checkbox"
              checked={settings.trustRemoteCode}
              onChange={(event) => update({ trustRemoteCode: event.target.checked })}
            />
          </div>
          {hasVisragDimensionMismatch ? (
            <p className="inline-alert inline-alert--error">
              The transformers backend should use vector size 2304 for openbmb/VisRAG-Ret. A mismatched
              collection will reject page embeddings until it is recreated.
            </p>
          ) : null}
        </div>

        <div className="setup-section">
          <h3>3. Local services</h3>
          <div className="field-grid setup-field-grid">
            <div className="field">
              <label htmlFor="setup-api-url">FastAPI URL</label>
              <input
                id="setup-api-url"
                type="url"
                value={settings.apiBaseUrl}
                onChange={(event) => update({ apiBaseUrl: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="setup-qdrant-url">Qdrant URL</label>
              <input
                id="setup-qdrant-url"
                type="url"
                value={settings.qdrantUrl}
                onChange={(event) => update({ qdrantUrl: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="setup-storage">Storage root</label>
              <input
                id="setup-storage"
                type="text"
                value={settings.storageRoot}
                onChange={(event) => update({ storageRoot: event.target.value })}
              />
            </div>
          </div>
        </div>

        <div className="setup-section">
          <h3>4. Multimodal context</h3>
          <div className="toggle">
            <label htmlFor="setup-multimodal-context">Attach retrieved page images</label>
            <input
              id="setup-multimodal-context"
              type="checkbox"
              checked={settings.useMultimodalContext}
              onChange={(event) => update({ useMultimodalContext: event.target.checked })}
            />
          </div>
          <div className="field">
            <label htmlFor="setup-max-evidence-images">Max evidence images</label>
            <input
              id="setup-max-evidence-images"
              type="number"
              min="0"
              max="10"
              value={settings.maxEvidenceImages}
              onChange={(event) =>
                update({ maxEvidenceImages: Math.min(10, Math.max(0, Number(event.target.value))) })
              }
            />
          </div>
          <p className="small-muted">
            Use a vision-capable OpenAI-compatible provider/model when this is enabled. Text-only
            models should leave it off and rely on the EVisRAG-style evidence prompt.
          </p>
        </div>

        <div className="setup-section">
          <h3>5. Generation provider</h3>
          <div className="field-grid setup-field-grid">
            <div className="field">
              <label htmlFor="setup-provider">Company</label>
              <select
                id="setup-provider"
                value={activePreset?.company ?? "Custom"}
                onChange={(event) => applyProvider(event.target.value)}
              >
                {providerPresets.map((preset) => (
                  <option key={preset.company} value={preset.company}>
                    {preset.company}
                  </option>
                ))}
              </select>
            </div>
            {showCompanyLabelInput ? (
              <div className="field">
                <label htmlFor="setup-provider-label">Company label</label>
                <input
                  id="setup-provider-label"
                  type="text"
                  value={settings.providerCompany}
                  onChange={(event) => update({ providerCompany: event.target.value })}
                  placeholder="My local endpoint"
                />
              </div>
            ) : null}
            <div className="field">
              <label htmlFor="setup-provider-base">Base URL</label>
              <input
                id="setup-provider-base"
                type="url"
                value={settings.providerBaseUrl}
                onChange={(event) => update({ providerBaseUrl: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="setup-provider-model">Model</label>
              <input
                id="setup-provider-model"
                type="text"
                value={settings.providerModel}
                onChange={(event) => update({ providerModel: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="setup-provider-key">API key</label>
              <input
                id="setup-provider-key"
                type="password"
                value={settings.providerApiKey}
                onChange={(event) => update({ providerApiKey: event.target.value })}
                placeholder="Saved locally in this browser"
                autoComplete="off"
              />
            </div>
          </div>
          <p className="small-muted">{selectedPreset.note}</p>
        </div>

        <div className="setup-section setup-section--wide">
          <h3>6. Generated local settings</h3>
          <pre className="env-preview">{envPreview(settings)}</pre>
          <div className="command-grid" aria-label="Install commands">
            <code>docker compose up -d qdrant</code>
            <code>pip install -e &quot;.[dev]&quot;</code>
            <code>pip install -e &quot;.[visrag]&quot;</code>
            <code>npm install &amp;&amp; npm run dev</code>
          </div>
        </div>
      </div>
    </section>
  );
}
