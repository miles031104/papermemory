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
                <div
                  className="pricing-card__price"
                  aria-label={`${plan.name} price ${plan.price} ${plan.audience}`}
                >
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
                aria-label={
                  isSelected ? `${plan.name} preview selected` : `Select ${plan.name} preview`
                }
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
