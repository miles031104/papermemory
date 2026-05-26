import type { InstallMode, InstallSettings, ModelSettings } from "@/lib/types";

interface SetupWizardProps {
  settings: InstallSettings;
  modelSettings: ModelSettings;
  onChange: (settings: InstallSettings) => void;
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

function envPreview(settings: InstallSettings, modelSettings: ModelSettings) {
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
    `PAPERMEMORY_BYOK_ENABLE_IMAGE_CONTEXT=${modelSettings.useMultimodalContext ? "true" : "false"}`,
    `PAPERMEMORY_BYOK_MAX_EVIDENCE_IMAGES=${modelSettings.maxEvidenceImages}`,
    `PAPERMEMORY_BYOK_MAX_IMAGE_BYTES=2097152`,
    `PAPERMEMORY_BYOK_BASE_URL=${modelSettings.baseUrl}`,
    `PAPERMEMORY_BYOK_MODEL=${modelSettings.model}`
  ];

  if (modelSettings.apiKey.trim()) {
    lines.push("PAPERMEMORY_BYOK_API_KEY=<provided in Model settings>");
  }

  if (settings.hfToken.trim()) {
    lines.push("HF_TOKEN=<provided in this setup session>");
  }

  return lines.join("\n");
}

export function SetupWizard({ settings, modelSettings, onChange }: SetupWizardProps) {
  const update = (patch: Partial<InstallSettings>) => onChange({ ...settings, ...patch });
  const isRealVisrag = settings.visragBackend === "transformers";
  const hasVisragDimensionMismatch = isRealVisrag && settings.qdrantVectorSize !== 2304;

  return (
    <section className="panel setup-panel" aria-labelledby="setup-title">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Install setup</p>
          <h2 id="setup-title">Configure local PaperMemory</h2>
          <p>Configure local retrieval, storage, and generated env values.</p>
        </div>
      </div>

      <div className="setup-grid setup-grid--compact">
        <div className="setup-section setup-section--essential">
          <h3>API connection</h3>
          <div className="field">
            <label htmlFor="setup-api-url">FastAPI URL</label>
            <input
              id="setup-api-url"
              type="url"
              value={settings.apiBaseUrl}
              onChange={(event) => update({ apiBaseUrl: event.target.value })}
            />
          </div>
          <p className="small-muted">Used by upload, library management, retrieval, and chat.</p>
        </div>

        <details className="settings-disclosure setup-disclosure">
          <summary>Install mode and local services</summary>
          <div className="settings-disclosure__body">
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
            <div className="field-grid setup-field-grid">
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
        </details>

        <details className="settings-disclosure setup-disclosure">
          <summary>VisRAG and Hugging Face</summary>
          <div className="settings-disclosure__body">
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
        </details>

        <details className="settings-disclosure setup-disclosure">
          <summary>Generated local settings</summary>
          <div className="settings-disclosure__body">
            <pre className="env-preview">{envPreview(settings, modelSettings)}</pre>
            <div className="command-grid" aria-label="Install commands">
              <code>docker compose up -d qdrant</code>
              <code>pip install -e &quot;.[dev]&quot;</code>
              <code>pip install -e &quot;.[visrag]&quot;</code>
              <code>npm install &amp;&amp; npm run dev</code>
            </div>
          </div>
        </details>
      </div>
    </section>
  );
}
