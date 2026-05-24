# Agent Framework Reference

Source: `D:\Download\Hello-Agents-V1.0.2-20260210.pdf`

This note records the parts of the Hello-Agents teaching framework that should
guide future PaperMemory agent work. It is a project-specific adaptation, not a
plan to copy the HelloAgents package directly.

## Why It Matters

Hello-Agents frames an agent as a loop over perception, thought, action, and
observation. For PaperMemory, that maps cleanly to a research assistant that
receives a user question, selects local paper evidence, builds a compact
evidence context, calls a BYOK model provider, and returns an answer with page
citations and explicit limits.

The useful design stance is:

- Prefer AI-native agent behavior over a rigid workflow engine.
- Keep the framework understandable, modular, and locally controllable.
- Treat tools, memory, retrieval, protocol adapters, and evaluation as explicit
  system components with stable contracts.
- Make evidence and failures visible to the user, while keeping private
  reasoning and internal process logs out of the answer.

## Architecture Principles To Reuse

Hello-Agents' Chapter 7 summarizes its framework principles as layered
decoupling, single responsibility, and unified interfaces. PaperMemory should
use the same shape:

- Agent contract: one public orchestration boundary for chat/research behavior.
- Model gateway: one provider-neutral interface for OpenAI-compatible BYOK
  models and future provider adapters.
- Tool system: narrow tools with clear inputs, outputs, errors, and scope.
- Message/context system: structured records for user messages, retrieved
  evidence, citations, model outputs, and limits.
- Storage boundary: local-first persistence for papers, page images, metadata,
  conversations, and future memory.

Avoid over-abstracting before the product needs it. The first-class PaperMemory
runtime is still a local PDF research workspace, not a general-purpose agent SDK.

## Agent Patterns

Use these patterns selectively:

- ReAct: best for iterative retrieval and evidence follow-up, where each
  observation can change the next retrieval or citation decision.
- Plan-and-Solve: best for longer research tasks, literature comparison, or
  multi-paper synthesis. Generate a short plan, execute against evidence, then
  answer.
- Reflection: best as a validation pass for citation coverage, unsupported
  claims, missing limits, and provider quirks. Do not expose the reflection text
  to users.

For the current MVP chat path, PaperMemory should remain evidence-first and
mostly single-agent. Multi-agent decomposition is useful later for deep research,
where separate planner, evidence summarizer, and report writer roles can keep
their contexts cleaner.

## Memory And Retrieval

Hello-Agents separates memory from RAG. PaperMemory should keep that distinction:

- RAG/retrieval answers the question: "Which paper pages support this turn?"
- Memory answers the question: "What persistent user, project, paper, and
  conversation facts should survive across turns?"

Initial memory layers should be conservative:

- Working memory: current conversation, selected library/group, active papers,
  and retrieved evidence.
- Episodic memory: prior conversations and research sessions, stored locally.
- Semantic memory: durable paper notes, concepts, claims, and relationships.
- Perceptual memory: page images, figures, tables, and OCR/page metadata.

Do not let memory override retrieved paper evidence. If memory conflicts with
page evidence, the answer should say so and prefer the page evidence.

## Context Engineering

Hello-Agents treats context engineering as a runtime pipeline, not just prompt
writing. PaperMemory should use a similar Gather -> Select -> Structure ->
Compress discipline:

1. Gather: user question, active scope, recent conversation, candidate pages,
   paper metadata, and relevant memory notes.
2. Select: keep only high-signal, scoped, recent, and evidence-bearing items.
3. Structure: separate instructions, scope, evidence, conversation, and output
   contract into stable prompt sections.
4. Compress: summarize older conversation and long evidence snippets before
   they pollute the model context.

Useful constraints:

- Context is a limited attention budget; more retrieved pages are not always
  better.
- Tools should return token-friendly summaries plus stable references, such as
  `paper_id p.N` and browser-safe evidence image URLs.
- Prefer just-in-time retrieval over eagerly stuffing all candidate paper
  metadata into the prompt.
- Keep structured notes outside the model context and retrieve them only when
  relevant.

## Tool And Protocol Design

Hello-Agents' protocol chapter wraps MCP, A2A, and ANP behind tool interfaces.
PaperMemory should apply the same idea without committing to a protocol too
early:

- Treat local retrieval, page rendering, note lookup, citation checking, and
  provider calls as tool-like capabilities with explicit contracts.
- Keep protocol adapters behind the same tool boundary if MCP or external agent
  integrations are added later.
- Favor a minimum viable tool set. Ambiguous overlapping tools make model
  behavior less stable.
- Tool outputs should include enough structured metadata for audit and UI
  rendering, not just prose.

## Evaluation

Hello-Agents emphasizes evaluating agent changes rather than trusting prompt
intuition. PaperMemory agent work should add or preserve tests for:

- Tool-call and retrieval behavior under empty, scoped, and multi-paper states.
- Citation format stability: `paper_id p.N`.
- Unsupported-claim prevention when evidence is weak or missing.
- Hidden reasoning redaction and provider malformed-output handling.
- Image-context honesty when a provider cannot inspect page images.
- Latency and token growth for larger libraries.

For future deep-research features, add benchmark-style fixtures for planning,
source deduplication, evidence coverage, and final report citation quality.

## Product-Specific Guardrails

- Local-first remains the trust model. Do not add hosted storage, shared keys, or
  remote indexing as hidden defaults.
- BYOK remains explicit. Provider keys should not be written to project files by
  default.
- Page-image retrieval is the primary evidence path. Text-only shortcuts should
  be labeled as such.
- User-facing answers should show answer, evidence, and limits. They should not
  show chain-of-thought, scratchpads, or internal orchestration logs.
- Settings and provider configuration should stay separate from the main
  research workspace.

## Implementation Checklist

Before adding or changing an agent feature, check:

- Which agent pattern is actually needed: direct answer, ReAct, plan-and-solve,
  reflection, or multi-agent deep research?
- What is the exact evidence boundary: library, group, paper, pages, memory, or
  general model knowledge?
- Which tools are available, and are their contracts narrow enough for stable
  use?
- How is context gathered, selected, structured, and compressed?
- What visible output contract will the user see?
- What tests prove citations, failure behavior, hidden reasoning redaction, and
  scope handling still work?

