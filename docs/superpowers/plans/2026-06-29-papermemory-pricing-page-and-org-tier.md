# PaperMemory Pricing Page and Organization Tier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a front-end-only pricing/plan selection view for Free, Starter, Pro, and Organization tiers, and mention the 50 USD/month organization tier once in the final report.

**Architecture:** The UI change is local to the Next.js web app and does not add payment, authentication, account state, or backend APIs. A new `PricingView` component renders static plan cards with client-side selected-card highlighting; `WorkspaceView` and sidebar navigation expose it as a first-class demo page. The report change is one bounded paragraph in the Product and Revenue Logic section, preserving the existing cost model and avoiding unsupported claims about organization-tier margins.

**Tech Stack:** Next.js 15, React 19, TypeScript, existing CSS in `apps/web/app/globals.css`, LaTeX final report compiled with bundled Tectonic.

---

## File Structure

- Create: `apps/web/components/pricing-view.tsx`
  - Responsibility: Static pricing-plan UI and local selected-plan state.
  - No backend dependency, no checkout action, no persistence.
- Modify: `apps/web/lib/types.ts`
  - Responsibility: Extend `WorkspaceView` union with `"plans"`.
- Modify: `apps/web/components/research-sidebar.tsx`
  - Responsibility: Add `Plans` to the sidebar view navigation.
- Modify: `apps/web/components/workspace-client.tsx`
  - Responsibility: Import and render `PricingView` when `activeView === "plans"`.
- Modify: `apps/web/app/globals.css`
  - Responsibility: Add responsive pricing-grid/card styles matching the current app surface.
- Modify: `reports/final/main.tex`
  - Responsibility: Add one organization-tier paragraph after the existing 10/20 USD packaging paragraph.
- Generated: `reports/final/main.pdf`
  - Responsibility: Recompiled final PDF after the LaTeX paragraph change.

---

## Implementation Tasks

### Task 1: Add The Pricing View Route Surface

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/components/research-sidebar.tsx`
- Modify: `apps/web/components/workspace-client.tsx`
- Create: `apps/web/components/pricing-view.tsx`

- [ ] **Step 1: Extend the workspace view union**

In `apps/web/lib/types.ts`, replace:

```ts
export type WorkspaceView = "home" | "chat" | "papers" | "settings";
```

with:

```ts
export type WorkspaceView = "home" | "chat" | "papers" | "plans" | "settings";
```

- [ ] **Step 2: Add Plans to sidebar navigation**

In `apps/web/components/research-sidebar.tsx`, replace the `workspaceViews` array with:

```ts
const workspaceViews: Array<{ id: WorkspaceView; label: string }> = [
  { id: "home", label: "Home" },
  { id: "chat", label: "Chat" },
  { id: "papers", label: "Paper Manager" },
  { id: "plans", label: "Plans" },
  { id: "settings", label: "Settings" },
];
```

- [ ] **Step 3: Create the static PricingView component**

Create `apps/web/components/pricing-view.tsx` with:

```tsx
"use client";

import { useState } from "react";

type PlanId = "free" | "starter" | "pro" | "organization";

interface PricingPlan {
  id: PlanId;
  name: string;
  price: string;
  audience: string;
  badge: string;
  description: string;
  features: string[];
  usage: string;
}

const plans: PricingPlan[] = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    audience: "BYOK trial",
    badge: "Local-first",
    description: "Start with local PDF evidence work while keeping model spend outside PaperMemory.",
    features: [
      "Bring your own API key or local model path",
      "Limited paper groups for adoption testing",
      "Evidence cards, citations, and reliability status",
    ],
    usage: "Best for first setup and small reading projects.",
  },
  {
    id: "starter",
    name: "Starter",
    price: "$10",
    audience: "per month",
    badge: "Routine work",
    description: "Managed LLM access support for postgraduate users who do not want BYOK-only setup.",
    features: [
      "Provider-compliant API relay",
      "Lower weekly managed-model cap",
      "More groups for routine evidence runs",
    ],
    usage: "Best for weekly literature notes and first-pass citation checks.",
  },
  {
    id: "pro",
    name: "Pro",
    price: "$20",
    audience: "per month",
    badge: "Heavy reading",
    description: "A larger individual workspace for repeated drafting and heavier literature projects.",
    features: [
      "Higher weekly managed-model cap",
      "Larger workspace for literature projects",
      "BYOK fallback after managed allowance",
    ],
    usage: "Best for thesis chapters, reports, and repeated evidence scans.",
  },
  {
    id: "organization",
    name: "Organization",
    price: "$50",
    audience: "per month",
    badge: "Shared workspace",
    description: "A team-facing plan for shared literature libraries and notes across users.",
    features: [
      "Shared paper libraries for labs or small teams",
      "Shared notes around evidence packets",
      "Organization workspace for collaborative review",
    ],
    usage: "Best for research groups, labs, and small consulting teams.",
  },
];

export function PricingView() {
  const [selectedPlan, setSelectedPlan] = useState<PlanId>("starter");

  return (
    <section className="pricing-view" aria-labelledby="pricing-title">
      <header className="pricing-view__header">
        <div>
          <p className="eyebrow">Plans</p>
          <h2 id="pricing-title">Choose how PaperMemory supports your evidence workflow.</h2>
          <p>
            This is a product preview for the demo. Plan selection is front-end only and does not
            start billing or change model access.
          </p>
        </div>
      </header>

      <div className="pricing-grid" role="list">
        {plans.map((plan) => {
          const isSelected = selectedPlan === plan.id;

          return (
            <article
              className={`pricing-card${isSelected ? " pricing-card--selected" : ""}`}
              key={plan.id}
              role="listitem"
            >
              <div className="pricing-card__top">
                <div>
                  <span className="pricing-card__badge">{plan.badge}</span>
                  <h3>{plan.name}</h3>
                </div>
                <div className="pricing-card__price" aria-label={`${plan.name} price ${plan.price} ${plan.audience}`}>
                  <strong>{plan.price}</strong>
                  <span>{plan.audience}</span>
                </div>
              </div>

              <p className="pricing-card__description">{plan.description}</p>

              <ul className="pricing-card__features">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>

              <p className="pricing-card__usage">{plan.usage}</p>

              <button
                className={`button ${isSelected ? "button--primary" : "button--subtle"}`}
                type="button"
                aria-pressed={isSelected}
                onClick={() => setSelectedPlan(plan.id)}
              >
                {isSelected ? "Selected preview" : "Select preview"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Render the PricingView in the workspace**

In `apps/web/components/workspace-client.tsx`, add the import near other component imports:

```ts
import { PricingView } from "@/components/pricing-view";
```

Then add this render block after the Paper Manager block and before the Settings block:

```tsx
          {activeView === "plans" ? <PricingView /> : null}
```

- [ ] **Step 5: Run the front-end type check**

Run:

```powershell
npm run typecheck
```

from:

```powershell
D:\codex\papermemory\apps\web
```

Expected:

```text
> @papermemory/web@0.1.0 typecheck
> tsc --noEmit
```

with exit code 0 and no TypeScript errors.

---

### Task 2: Style The Pricing Page For The Existing App

**Files:**
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Add pricing layout styles**

Append this CSS after the existing `.settings-view` block styles, before responsive media queries:

```css
.pricing-view {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.pricing-view__header {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.075), rgba(255, 255, 255, 0.032)),
    rgba(12, 14, 21, 0.76);
  box-shadow: var(--shadow);
  padding: 18px 20px;
  backdrop-filter: blur(24px);
}

.pricing-view__header p {
  max-width: 820px;
  margin-bottom: 0;
  color: var(--text-muted);
  font-size: 0.88rem;
  line-height: 1.5;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.pricing-card {
  display: grid;
  grid-template-rows: auto auto 1fr auto auto;
  gap: 14px;
  min-width: 0;
  min-height: 430px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.078), rgba(255, 255, 255, 0.03)),
    rgba(12, 14, 21, 0.76);
  box-shadow: var(--shadow);
  padding: 18px;
  transition:
    border-color var(--transition),
    box-shadow var(--transition),
    transform var(--transition);
}

.pricing-card:hover,
.pricing-card--selected {
  border-color: rgba(142, 233, 210, 0.38);
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.pricing-card--selected {
  background:
    linear-gradient(180deg, rgba(142, 233, 210, 0.14), rgba(143, 183, 255, 0.055)),
    rgba(12, 14, 21, 0.8);
}

.pricing-card__top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
}

.pricing-card__badge {
  display: inline-flex;
  width: fit-content;
  border: 1px solid rgba(142, 233, 210, 0.26);
  border-radius: 999px;
  color: var(--accent-strong);
  background: rgba(142, 233, 210, 0.09);
  padding: 5px 9px;
  font-size: 0.72rem;
  font-weight: 850;
}

.pricing-card h3 {
  margin-top: 12px;
  font-size: 1.3rem;
}

.pricing-card__price {
  display: grid;
  gap: 2px;
  justify-items: end;
  text-align: right;
}

.pricing-card__price strong {
  font-size: 1.65rem;
  line-height: 1;
}

.pricing-card__price span,
.pricing-card__usage,
.pricing-card__description {
  color: var(--text-muted);
  font-size: 0.86rem;
  line-height: 1.45;
}

.pricing-card__features {
  display: grid;
  align-content: start;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.pricing-card__features li {
  position: relative;
  padding-left: 18px;
  color: var(--text);
  font-size: 0.86rem;
  line-height: 1.42;
}

.pricing-card__features li::before {
  position: absolute;
  left: 0;
  top: 0.42em;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--accent);
  content: "";
}
```

- [ ] **Step 2: Add responsive pricing rules**

Inside the existing responsive section near the bottom of `apps/web/app/globals.css`, add:

```css
@media (max-width: 1180px) {
  .pricing-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .pricing-grid {
    grid-template-columns: 1fr;
  }

  .pricing-card {
    min-height: 0;
  }

  .pricing-card__top {
    grid-template-columns: 1fr;
  }

  .pricing-card__price {
    justify-items: start;
    text-align: left;
  }
}
```

- [ ] **Step 3: Run type check again**

Run:

```powershell
npm run typecheck
```

from:

```powershell
D:\codex\papermemory\apps\web
```

Expected: exit code 0.

- [ ] **Step 4: Run production build**

Run:

```powershell
npm run build
```

from:

```powershell
D:\codex\papermemory\apps\web
```

Expected: Next.js build exits 0.

---

### Task 3: Add The Organization Tier To The Report

**Files:**
- Modify: `reports/final/main.tex`
- Generated: `reports/final/main.pdf`

- [ ] **Step 1: Add one bounded organization-tier paragraph**

In `reports/final/main.tex`, after this paragraph:

```tex
The proposed packaging follows the interview signal. The free tier is BYOK with limited groups, which lowers adoption friction and keeps model cost outside the product. The 10~USD/month tier adds provider-compliant API relay for managed LLM access with a lower weekly managed-model allowance for routine postgraduate work. The 20~USD/month tier offers a larger workspace and a higher weekly managed-model allowance for heavier literature projects. The paid design assumes commercial API access or equivalent provider permission; it does not rely on consumer-account pooling, coding-plan resale, or unlimited inference. The exact quotas should be set only after usage telemetry exists; this report intentionally does not invent them.
```

insert:

```tex
A later 50~USD/month organization tier could extend the same evidence workflow to small labs, research groups, or consulting teams by supporting shared literature libraries and shared notes across users. This tier is framed as collaborative workspace value rather than higher individual model usage; its economics would require separate telemetry on seats, storage, collaboration patterns, and support cost.
```

- [ ] **Step 2: Recompile the final PDF**

Run:

```powershell
python 'C:\Users\Miles CUI\.codex\plugins\cache\openai-bundled\latex\0.2.2\scripts\compile_latex.py' 'D:\codex\papermemory\reports\final\main.tex' --compiler tectonic
```

from:

```powershell
D:\codex\papermemory
```

Expected:

```text
Compiler: tectonic
Exit code: 0
PDF: D:\codex\papermemory\reports\final\main.pdf
```

- [ ] **Step 3: Check page count and organization-tier text**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; python -c "from pypdf import PdfReader; r=PdfReader('reports/final/main.pdf'); text='\n'.join((p.extract_text() or '') for p in r.pages); print('pages', len(r.pages)); print('org_tier', '50 USD/month organization tier' in text or '50 USD/month' in text); print('references', 'References' in text); print('appendix', 'Appendix' in text)"
```

from:

```powershell
D:\codex\papermemory
```

Expected:

```text
pages 12
org_tier True
references True
appendix True
```

If the page count increases, keep the organization paragraph but shorten it to:

```tex
A later 50~USD/month organization tier could target small labs and research teams by adding shared literature libraries and shared notes across users. Its economics would require separate telemetry on seats, storage, collaboration, and support cost.
```

Then recompile and repeat the page-count check.

---

### Task 4: Visual Demo Verification

**Files:**
- Read-only verification of `apps/web` output.

- [ ] **Step 1: Start the web dev server**

Run:

```powershell
npm run dev
```

from:

```powershell
D:\codex\papermemory\apps\web
```

Expected: Next.js starts and prints a local URL, usually `http://localhost:3000`. If port 3000 is occupied, use the port printed by Next.js.

- [ ] **Step 2: Open the app and check the Plans tab**

Use the browser or Playwright to open the printed local URL. Check:

- Sidebar includes `Plans`.
- Clicking `Plans` shows four cards: `Free`, `Starter`, `Pro`, `Organization`.
- Prices are `$0`, `$10`, `$20`, `$50`.
- The Starter and Pro cards clearly distinguish lower vs higher weekly managed-model caps.
- The Organization card says shared literature libraries and shared notes across users.
- Clicking a card changes the selected-card state only; it does not call an API or navigate to checkout.

- [ ] **Step 3: Check responsive layout**

Use desktop and mobile widths. Check:

- Desktop shows a readable multi-card layout.
- Medium width collapses to two columns.
- Mobile width collapses to one column.
- No button text overlaps.
- No pricing-card text escapes its container.

---

### Task 5: Final Safety Scan

**Files:**
- Modified files from Tasks 1 through 3.

- [ ] **Step 1: Scan for unsupported billing claims**

Run:

```powershell
rg -n "checkout|payment|Stripe|unlimited|guaranteed|production margin|account pooling|coding-plan resale|resale" apps/web reports/final/main.tex reports/final/tables
```

Expected:

- No new `checkout`, `payment`, or `Stripe` implementation claim.
- No `unlimited` usage promise.
- No account-pooling or coding-plan resale claim.
- Existing warnings about not relying on account pooling or unlimited inference may remain.

- [ ] **Step 2: Inspect git diff for tight scope**

Run:

```powershell
git diff -- apps/web/components/pricing-view.tsx apps/web/lib/types.ts apps/web/components/research-sidebar.tsx apps/web/components/workspace-client.tsx apps/web/app/globals.css reports/final/main.tex reports/final/main.pdf
```

Expected:

- UI diff is limited to navigation, static pricing component, and styles.
- Report diff is limited to one organization-tier paragraph and regenerated PDF.
- No backend API, database, auth, or payment code is added.

- [ ] **Step 3: Whitespace check**

Run:

```powershell
git diff --check -- apps/web/components/pricing-view.tsx apps/web/lib/types.ts apps/web/components/research-sidebar.tsx apps/web/components/workspace-client.tsx apps/web/app/globals.css reports/final/main.tex
```

Expected: exit code 0.

---

## Self-Review

- Spec coverage: The plan covers the static front-end pricing interface, all four requested tiers, the 10/20 USD distinction, the 50 USD organization tier with shared libraries and notes, and the one-paragraph report update.
- Scope control: No backend payment, authentication, persistence, quota enforcement, or real billing is introduced.
- Claim boundary: Report wording frames the 50 USD tier as a later proposed organization tier and does not attach unsupported margin, conversion, retention, or production-cost claims.
- Verification: TypeScript typecheck, Next.js build, LaTeX compile, PDF page-count check, visual layout check, unsupported-claim scan, and `git diff --check` are all included.
