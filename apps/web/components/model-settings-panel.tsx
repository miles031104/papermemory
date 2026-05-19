import { findProviderPreset, providerPresets } from "@/lib/provider-presets";
import type { ModelSettings } from "@/lib/types";

interface ModelSettingsPanelProps {
  settings: ModelSettings;
  onChange: (settings: ModelSettings) => void;
}

export function ModelSettingsPanel({ settings, onChange }: ModelSettingsPanelProps) {
  const updateSettings = (patch: Partial<ModelSettings>) => {
    onChange({ ...settings, ...patch });
  };
  const activePreset = findProviderPreset(settings.providerCompany);
  const customPreset = findProviderPreset("Custom") ?? providerPresets[0];
  const selectedPreset = activePreset ?? customPreset;
  const showCompanyLabelInput = !activePreset || activePreset.company === "Custom";

  const applyPreset = (company: string) => {
    const preset = findProviderPreset(company);
    if (!preset) {
      return;
    }
    updateSettings({
      providerCompany: preset.company,
      baseUrl: preset.baseUrl,
      model: preset.model
    });
  };

  return (
    <section className="panel" aria-labelledby="settings-title">
      <div className="panel__header">
        <div>
          <h2 id="settings-title">Model settings</h2>
          <p>Bring your own multimodal API key for answer generation.</p>
        </div>
      </div>
      <form
        className="panel__body settings-stack"
        aria-label="Model settings"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="field">
          <label htmlFor="provider">Provider</label>
          <select
            id="provider"
            name="provider"
            value={settings.provider}
            onChange={() => updateSettings({ provider: "openai-compatible" })}
          >
            <option value="openai-compatible">OpenAI compatible</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="provider-company">Company</label>
          <select
            id="provider-company"
            name="provider-company"
            value={activePreset?.company ?? "Custom"}
            onChange={(event) => applyPreset(event.target.value)}
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
            <label htmlFor="provider-company-label">Company label</label>
            <input
              id="provider-company-label"
              name="provider-company-label"
              type="text"
              value={settings.providerCompany}
              onChange={(event) => updateSettings({ providerCompany: event.target.value })}
              placeholder="My local endpoint"
            />
          </div>
        ) : null}

        <div className="field">
          <label htmlFor="base-url">Base URL</label>
          <input
            id="base-url"
            name="base-url"
            type="url"
            value={settings.baseUrl}
            onChange={(event) => updateSettings({ baseUrl: event.target.value })}
            placeholder="https://api.openai.com/v1"
          />
        </div>

        <div className="field">
          <label htmlFor="model">Model</label>
          <input
            id="model"
            name="model"
            type="text"
            value={settings.model}
            onChange={(event) => updateSettings({ model: event.target.value })}
          />
        </div>

        <div className="field">
          <label htmlFor="api-key">API key</label>
          <input
            id="api-key"
            name="api-key"
            type="password"
            value={settings.apiKey}
            onChange={(event) => updateSettings({ apiKey: event.target.value })}
            placeholder="Kept only in this browser session"
            autoComplete="off"
          />
        </div>

        <div className="slider-row">
          <label htmlFor="temperature">Temperature: {settings.temperature}</label>
          <input
            id="temperature"
            name="temperature"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={settings.temperature}
            onChange={(event) => updateSettings({ temperature: Number(event.target.value) })}
          />
        </div>

        <div className="slider-row">
          <label htmlFor="retrieval-top-k">Retrieval top-k: {settings.retrievalTopK}</label>
          <input
            id="retrieval-top-k"
            name="retrieval-top-k"
            type="range"
            min="1"
            max="25"
            step="1"
            value={settings.retrievalTopK}
            onChange={(event) => updateSettings({ retrievalTopK: Number(event.target.value) })}
          />
        </div>

        <div className="toggle">
          <label htmlFor="evidence-only">Require page evidence</label>
          <input
            id="evidence-only"
            name="evidence-only"
            type="checkbox"
            checked={settings.requireEvidence}
            onChange={(event) => updateSettings({ requireEvidence: event.target.checked })}
          />
        </div>

        <div className="toggle">
          <label htmlFor="image-context">Attach page images</label>
          <input
            id="image-context"
            name="image-context"
            type="checkbox"
            checked={settings.useMultimodalContext}
            onChange={(event) => updateSettings({ useMultimodalContext: event.target.checked })}
          />
        </div>

        <div className="field">
          <label htmlFor="max-evidence-images">Max evidence images</label>
          <input
            id="max-evidence-images"
            name="max-evidence-images"
            type="number"
            min="0"
            max="10"
            value={settings.maxEvidenceImages}
            onChange={(event) =>
              updateSettings({ maxEvidenceImages: Math.min(10, Math.max(0, Number(event.target.value))) })
            }
          />
        </div>

        <p className="small-muted">
          {selectedPreset.note} The API key stays in React state and is sent only with chat requests.
        </p>
      </form>
    </section>
  );
}
