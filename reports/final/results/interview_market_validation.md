# Interview market validation

This artifact records the market evidence used for the final-report rewrite. The evidence comes from informal interviews with 10 postgraduate interviewees.

## Questionnaire protocol

Each interview used the same six prompts:

1. Research stage and PDF reading frequency.
2. Current literature reading and citation-checking workflow.
3. 1-5 conditional likelihood to pay if PaperMemory delivers local PDF ingestion, evidence-backed answers, visible page citations, bounded uncertainty, and smoother model access.
4. Preference between BYOK/local-model setup and PaperMemory-provided LLM access through a subscription.
5. Preferred packaging among free BYOK with limited groups, 10 USD/month with a lower weekly managed-model limit, and 20 USD/month with a higher weekly managed-model limit.
6. Risk that would stop the interviewee from relying on the tool for research writing.

## Interview aggregate

| Measure | Result | Report use |
| --- | ---: | --- |
| Sample size | 10 researchers | Small postgraduate convenience sample. |
| Conditional purchase likelihood | 4.2 / 5 mean | Early willingness-to-pay evidence if PaperMemory delivers the claimed functions. |
| Preferred access model | 70% prefer PaperMemory-provided API/model access | Supports a paid subscription option instead of a BYOK-only product. |

The purchase-likelihood score is conditional. Participants were asked about willingness to pay if PaperMemory delivers the claimed workflow: local PDF ingestion, evidence-backed answers, visible page citations, bounded uncertainty, and smoother model access.

The access preference means 70% preferred a monthly subscription with PaperMemory-provided API/model access over a BYOK-only product. The report frames this as provider-compliant API relay or commercial API access, not consumer subscription resale.

## Proposed packaging

The proposed model is a freemium product boundary:

- Free BYOK tier with limited groups and no included model spend.
- 10 USD/month tier with provider-compliant PaperMemory-managed LLM API relay and a lower weekly managed-model limit.
- 20 USD/month tier with provider-compliant PaperMemory-managed LLM API relay and a higher weekly managed-model limit.

The paid tiers are proposed, not launched. Weekly caps, BYOK fallback above cap, rate limits, and fair-use controls are product controls, not validated pricing telemetry. The cost logic should be read together with `reports/final/results/cost_benefit.md`: current 10-PDF and 30-PDF stress-test scenarios estimate low API/compute cost relative to saved first-pass evidence-gathering labor, but they do not include production hosting, support, sales, abuse handling, or full licensing cost.

## Boundaries

These interviews are early willingness-to-pay evidence, not product-market fit. The sample is small. The result measures conditional intent, not participant-level raw data, actual paid conversion, payment completion, retention, referral, or production revenue. It also does not prove that the 10 USD/month or 20 USD/month tiers are profitable at scale. The report can use the numbers to justify a plausible commercial direction, but it should keep the claim tied to early postgraduate interview feedback and bounded cost assumptions.
