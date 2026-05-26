import { ModelSettingsPanel } from "@/components/model-settings-panel";
import { SetupWizard } from "@/components/setup-wizard";
import type { InstallSettings, ModelSettings } from "@/lib/types";

interface SettingsViewProps {
  modelSettings: ModelSettings;
  installSettings: InstallSettings;
  apiDetail: string;
  onModelSettingsChange: (settings: ModelSettings) => void;
  onInstallSettingsChange: (settings: InstallSettings) => void;
}

export function SettingsView({
  modelSettings,
  installSettings,
  apiDetail,
  onModelSettingsChange,
  onInstallSettingsChange
}: SettingsViewProps) {
  return (
    <div className="settings-view" aria-label="PaperMemory settings">
      <header className="settings-view__header">
        <div>
          <p className="eyebrow">Settings</p>
          <h2>Local model and install setup</h2>
          <p>{apiDetail}</p>
        </div>
      </header>

      <div className="settings-view__content">
        <div className="settings-view__model">
          <ModelSettingsPanel settings={modelSettings} onChange={onModelSettingsChange} />
        </div>
        <SetupWizard
          settings={installSettings}
          modelSettings={modelSettings}
          onChange={onInstallSettingsChange}
        />
      </div>
    </div>
  );
}
