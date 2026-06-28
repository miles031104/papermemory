# Node 0 Reproducibility Environment

Date recorded: 2026-06-24

## Baseline

- Repository: `D:\codex\llm_paper_assis\papermemory`
- Working branch: `codex/papermemory-evidence-agent`
- Working commit: `6884d738df9d685bad4f5a673a7d13a7bc2fb691`
- Authoritative baseline: `origin/miles` at `6884d738df9d685bad4f5a673a7d13a7bc2fb691`
- Baseline subject: `feat: expand paper manager and agentic retrieval`
- Node 0 scope: documentation and verification only; no feature code changes.

## Local Toolchain

- Python: `Python 3.12.7`
- Node.js: `v22.18.0`
- npm: `10.9.3`

## Smoke Commands Recorded

### Git status

Command:

```powershell
git status --short --branch
```

Exit status: 0

Output:

```text
warning: could not open directory '.tmp_pytest_visrag_contract/base/': Permission denied
warning: could not open directory 'pytest-tmp/': Permission denied
## codex/papermemory-evidence-agent
untracked: .planning/
untracked: docs/superpowers/plans/2026-06-22-paper-memory-evidence-agent.md
```

Important warning: Git cannot enumerate two local pytest/temp directories. This is pre-existing local state and should be kept separate from feature work. The source plan and planning memory are currently untracked planning artifacts.

### Post-artifact git status

Command:

```powershell
git status --short --branch --untracked-files=all
```

Exit status: 0

Output after writing Node 0 artifacts:

```text
warning: could not open directory '.tmp_pytest_visrag_contract/base/': Permission denied
warning: could not open directory 'pytest-tmp/': Permission denied
## codex/papermemory-evidence-agent
untracked: .planning/.active_plan
untracked: .planning/2026-06-22-paper-memory-evidence-agent/findings.md
untracked: .planning/2026-06-22-paper-memory-evidence-agent/progress.md
untracked: .planning/2026-06-22-paper-memory-evidence-agent/task_plan.md
untracked: demo/local-run.md
untracked: docs/superpowers/plans/2026-06-22-paper-memory-evidence-agent.md
untracked: reports/final/results/reproducibility_environment.md
```

The Node 0 artifact directories visible in the final snapshot are `.planning/`, `demo/`, and `reports/final/results/`. No feature code, test files, package files, or lockfiles are part of the Node 0 artifact set.

### Web typecheck

Command:

```powershell
npm --prefix apps/web run typecheck
```

Exit status: 1

Result:

```text
components/chat-panel.tsx(4,27): error TS2307: Cannot find module 'react-markdown' or its corresponding type declarations.
components/chat-panel.tsx(5,23): error TS2307: Cannot find module 'remark-gfm' or its corresponding type declarations.
```

Dependency diagnostic:

```powershell
npm --prefix apps/web ls react-markdown remark-gfm --depth=0
```

Exit status: 1

```text
@papermemory/web@0.1.0 D:\codex\llm_paper_assis\papermemory\apps\web
`-- (empty)
```

`react-markdown` and `remark-gfm` are declared in `apps/web/package.json` and `package-lock.json`, but they are not installed in the current local `node_modules` tree. Node 0 did not run an install because package and lockfile writes are outside the allowed write scope for this node.

### API smoke subset

Command:

```powershell
python -m pytest apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_public_evidence_response.py -q
```

Exit status: 0

Result:

```text
25 passed in 2.79s
```

## Canonical Local Checks

- API smoke subset: `python -m pytest apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_public_evidence_response.py -q`
- Web typecheck: `npm --prefix apps/web run typecheck`
- Broader backend tests: `npm run test:api`
- Frontend typecheck alias: `npm run typecheck:web`
- Local integration smoke from README: `.\scripts\smoke-phase1-local.ps1`

## Latest-Code Surfaces To Preserve

Later nodes should extend these baseline surfaces instead of rebuilding them:

- Group-scoped paper, library, and conversation management.
- Current public `PageEvidence` shape with browser-safe `image_url` values and local path redaction.
- Page text captions stored in vector payloads as the existing display fallback.
- Chat request controls including `score_threshold`, `max_per_paper`, query rewrite, and default-on agentic retrieval.
- SSE `answer_stream` behavior with early evidence frames before token deltas.
- Markdown answer rendering, citation chips, evidence cards, and page preview behavior.
- Current bounded query planner over VisRAG page search.

## Node 0 Conclusion

The implementation base is pinned to the required `origin/miles` commit and the local execution environment has been recorded. The API smoke subset passes. The web typecheck currently fails because two declared frontend dependencies are missing from the local install tree; restore dependencies before treating frontend typecheck as a clean baseline.
