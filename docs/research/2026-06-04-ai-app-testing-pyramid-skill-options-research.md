---
date: 2026-06-04
updated: 2026-06-05
topic: ai-app-testing-pyramid-skill-options
source: engineer:research
handoff: ce-brainstorm-ready
linear_issue: BVA-480
---

# Research: AI Application Testing Pyramid Skill Options

## User Intent

Research and analyse the AI application testing pyramid practice, including how it was applied in this workshop repo, and decide whether to:

1. encode the practice as a new agent skill,
2. adopt an existing high-quality shared skill for AI app testing and evals, or
3. use another approach.

## Project Memory

### Current repo practice

The workshop repo already encodes a clear four-level pyramid in `requirements/Testing-Pyramid.md`:

1. **Level 1 — deterministic unit tests**: stub external/model boundaries to test orchestration, validation, tool routing, state/error handling, and formatting.
2. **Level 2 — constrained model tests**: call a real model with pinned model settings, temperature 0, structured output, and carefully controlled inputs.
3. **Level 3 — LLM-as-judge evals**: grade semantic quality and grounding with a judge model against explicit rubrics, with calibration needs.
4. **Level 4 — human evaluation**: expert review, preference testing, red-team notes, subjective quality, and safety/compliance review.

The implementation in this repo matches the pyramid well:

- `tests/test_level1.py` uses injected stubs and a fake Anthropic client for fast deterministic orchestration tests.
- `tests/test_level2.py` uses real Anthropic calls but controlled `StubSearchTool` fixtures, a pinned model, and temperature 0.
- `tests/test_level3.py` replays recorded Tavily fixtures by default, runs objective checks before judging, and then asks `claude-sonnet-4-6` to grade semantic dimensions.
- `tests/test_level4.py` is an explicit opt-in driver that creates a human-review packet and `xfail`s so manual judgment is not mistaken for automated success.

`docs/solutions/test-failures/stabilizing-level-3-llm-as-judge-tests-2026-06-02.md` captures the most transferable learning: replay retrieval fixtures by default, keep objective invariants in code, calibrate judge rubrics to the schema, and harden prompts/schema only when eval failures show real risks.

### KB-supported principles

Durable KB notes support the same pattern:

- `/Users/ota/d/m/notes-eng/llm-knowledge-base/wiki/evals/evals-as-validation-discipline.md` — evals are a validation discipline, not one tool; choose deterministic checks, LLM judges, or human judgment based on failure mode.
- `/Users/ota/d/m/notes-eng/llm-knowledge-base/wiki/evals/validation-gates-for-agentic-coding.md` — use layered validation gates; human review remains necessary for usefulness, taste, and domain fit.
- `/Users/ota/d/m/notes-eng/llm-knowledge-base/wiki/architecture/specification-precision-and-overspecification-risk.md` — deterministic orchestration benefits from precise specs/tests; probabilistic LLM behavior usually needs guardrails, evals, observability, and iteration rather than over-specified assertions.
- `/Users/ota/d/m/notes-eng/llm-knowledge-base/wiki/economics/cost-inversion-and-experiment-volume.md` — AI makes generation cheap, so validation, review, and deciding what to keep become the bottleneck.
- `/Users/ota/d/m/notes-eng/llm-knowledge-base/wiki/agents/agent-maturity-ladder.md` — mature agent systems need explicit validation, observability, budgets, governance, and human escalation, not only a prompt loop.

Follow-up KB-first searches found little evidence that the exact phrase “AI Agent Testing Pyramid” is already a durable local concept. The KB evidence is instead pattern-level: fast feedback loops, deterministic checks, observability, LLM-as-judge, and human review recur across local notes and course material. Relevant additional notes:

- `/Users/ota/d/m/notes-eng/ai/Courses/matt-pocock/AI SDK v5 Crash/06.md` — teaches deterministic scorers, LLM-as-judge, dev/CI/regression dataset tiers, and the warning that observability reveals real user behavior that imagined eval sets miss.
- `/Users/ota/d/m/notes-eng/llm-knowledge-base/raw/Post  LinkedIn 2.md` — Hamel Husain’s “Fix the Prompt Before Building an LLM-as-Judge” captures a useful cost hierarchy: clarify the prompt, add cheap code checks, then reserve LLM judges for persistent subjective problems.
- `/Users/ota/d/m/notes-eng/llm-knowledge-base/raw/writing-effective-tools-for-ai-agents.md` — Anthropic’s tool-design guidance uses realistic tasks, agent feedback, metrics, and held-out evals to iteratively improve tool ergonomics.
- `/Users/ota/d/m/notes-eng/blogs/evals.md` — local synthesis argues for hybrid high-signal automation plus structured human review, and warns that green eval dashboards can create false confidence if they measure the wrong thing.

## Online Context

### General AI app / agent eval practice

The strongest external signals came from official or high-reputation sources:

- Anthropic, **“Demystifying evals for AI agents”**: agent evals combine tasks, trials, graders, traces/transcripts, outcomes, harnesses, and suites. Anthropic recommends code-based graders where possible, model-based graders where necessary, and human graders for expert calibration. It also recommends starting with 20–50 real tasks, writing unambiguous tasks, using reference solutions to validate graders, and calibrating LLM judges with human experts.
  - URL: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Datadog, **“What Are LLM Evaluation Frameworks?”**: strong LLM eval frameworks use versioned datasets, fixed configurations, tracked prompts/models, deterministic checks, groundedness checks, LLM-as-judge rubrics, HITL review, production evaluation, and links from failing scores to traces.
  - URL: https://www.datadoghq.com/knowledge-center/llm-evaluation-frameworks/
- Block Engineering, **“Testing Pyramid for AI Agents”**: reframes the pyramid around tolerated uncertainty: deterministic foundations, replayed reality, probabilistic performance, and explicit judgment. It warns against live LLM tests in CI and favours deterministic CI plus on-demand higher layers.
  - URL: https://engineering.block.xyz/blog/testing-pyramid-for-ai-agents

These align closely with the workshop repo’s pyramid. The repo’s Level 3 replay fixture approach is especially consistent with the “replayed reality” / deterministic-middle-layer pattern.

### Actual practice evidence

The follow-up online research suggests that “AI/agent testing pyramid” is an emerging practitioner pattern, not a single settled standard. The repeated shape is consistent: keep the base deterministic and cheap; isolate or replay model/tool uncertainty where possible; add model-graded or scenario evals for semantic behavior; and keep human review or production monitoring for signals that cannot be reduced to stable assertions.

Practical examples and signals:

- **Block Engineering — “Testing Pyramid for AI Agents”**: reframes the pyramid around tolerated uncertainty rather than classic unit/integration/UI categories. Its layers are deterministic foundations, reproducible reality, probabilistic performance, and explicit judgment. It uses mock providers at the base, records/replays MCP and LLM interactions in the middle, aggregates benchmark success rates above that, and uses rubric/model judgment for quality. It explicitly says live LLM tests do not run in CI because they are too expensive, slow, and flaky; CI validates deterministic layers while humans validate higher layers when needed. URL: https://engineering.block.xyz/blog/testing-pyramid-for-ai-agents
- **Toucan — “AI Agent Backend Testing: The Pyramid We Use at Toucan”**: presents a production backend pyramid of unit/contract tests, integration tests with fake model outputs, and scenario replays from recorded real conversations. The article ties tests to observability: traces provide replay cases, and tests assert that structured events are emitted. URL: https://www.toucantoco.com/en/blog/ai-agent-testing-pyramid
- **Aashmawy support-agent example — “How I Test an AI Support Agent”**: publishes a six-layer repo-backed pyramid: pytest unit tests, property tests, component tests, integration tests with mocked OpenAI, trace-level behavioral contracts with replayed baselines, and live scenario/adversarial evals via Promptfoo/Garak. Its CI split mirrors the cost hierarchy: deterministic layers block PRs; live API-dependent layers are slower and conditional/informational. URL: https://dev.to/aashmawy/how-i-test-an-ai-support-agent-a-practical-testing-pyramid-3iik
- **Kevin Tan — “How to Test AI Agents Before They Break Production”**: reports a production-oriented three-layer version: unit tests with stub providers for deterministic logic, evals for output quality, and integration tests/nightly multi-trial full-loop checks. The minimum setup is pytest + mocked LLM, about 20 eval cases from real failures, and one CI gate. URL: https://blog.jztan.com/testing-ai-agents-in-production/
- **Anthropic — “Demystifying evals for AI agents”**: does not use a “pyramid” label as the primary frame, but its field-tested guidance matches the layered practice. It defines tasks, trials, graders, traces/transcripts, outcomes, harnesses, and suites; recommends code-based graders where possible, model-based graders where necessary, and human graders for calibration; recommends starting with 20–50 tasks drawn from manual checks, bugs, and real failures; and cites real internal/customer examples such as Claude Code, Descript, and Bolt. URL: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- **LangChain State of Agent Engineering survey**: provides adoption context rather than a pyramid recipe. Among 1,340 respondents, 57.3% report agents in production, 89% have some agent observability, 52.4% run offline evals, 37.3% run online evals, and teams running evals use both automated and human approaches: human review 59.8% and LLM-as-judge 53.3%. Quality is the leading production blocker at 32%. URL: https://www.langchain.com/state-of-agent-engineering
- **Rogério Chaves — “The Agent Testing Pyramid”**: describes a three-layer consulting/client pattern of unit tests, evals/optimization, and simulations, with simulations mapping directly to binary business outcomes. URL: https://rchaves.app/the-agent-testing-pyramid/

Synthesis: the practice is real enough to encode as a reusable decision discipline, but the exact levels vary by app and organization. “Pyramid” is best treated as an adaptive cost/confidence model rather than a canonical four-level framework. The workshop repo’s Level 1–4 pyramid is a strong teaching instance, not a universal schema.

### Existing shared skills and frameworks

Searches via `npx skills find` and skills.sh identified several candidates.

| Candidate | Evidence | Best fit | Caveats |
| --- | --- | --- | --- |
| `promptfoo/promptfoo@promptfoo-evals` | 144 installs on skills.sh; official Promptfoo repo has ~21.9k GitHub stars. Promptfoo docs explicitly publish this skill. | Declarative eval suites for prompts, agents, RAG, providers, JSON assertions, grounded rubrics, CI output, and skill evaluation. | Adds Promptfoo/YAML tooling; not needed for this workshop repo’s deliberately tiny pytest-first teaching flow. |
| `confident-ai/deepeval@deepeval` | 381 installs on skills.sh; official DeepEval repo has ~15.9k GitHub stars. | Python-first pytest eval suites, golden datasets, tracing, agent reasoning/action/execution metrics, optional Confident AI reporting. | Adds dependency and workflow surface area; too heavy for the current workshop’s “ten-minute comprehension” constraint. |
| `github/awesome-copilot@eval-driven-dev` | 2.8k installs on skills.sh; GitHub `awesome-copilot` repo has ~34.5k stars. | Pixie-style end-to-end eval-driven development for Python LLM apps with real LLM calls and controlled data injection. | Very opinionated and setup-heavy. Its rule “do not mock/stub the LLM” conflicts with the workshop’s Level 1 base tests unless scoped strictly to evals, not unit tests. |
| `daymade/claude-code-skills@promptfoo-evaluation` | 561 installs; repo has ~1.1k stars. | Promptfoo guidance for configs, Python custom assertions, LLM rubrics, model comparison. | Less authoritative than the official Promptfoo skill now available from `promptfoo/promptfoo`. |
| `datadog-labs/agent-skills@llm-obs-eval-pipeline` | 104 installs surfaced; Datadog repo has ~126 stars. | Production trace-driven eval bootstrapping from Datadog LLM Observability. | Only relevant when Datadog LLM Obs and `pup`/MCP are already in use. |
| `akillness/oh-my-skills@langsmith` | 168 installs surfaced; repo has ~22 stars. | LangSmith packet routing for tracing, evals, review queues, and experiments. | Useful only if LangSmith is already the chosen substrate; not a general default. |

Promptfoo’s official skill is particularly relevant because it teaches the agent to avoid common mistakes: use deterministic assertions before `llm-rubric`, inline source material for faithfulness rubrics, pin grader providers, use file-based tests, and produce CI-friendly outputs.

OpenAI’s **“Testing Agent Skills Systematically with Evals”** is also relevant if we build our own skill. It recommends evaluating skills like prompts: define success before writing the skill, include positive and negative trigger cases, capture traces/artifacts, start with deterministic checks, then add rubric-based grading where rules fall short.

- URL: https://developers.openai.com/blog/eval-skills
- Promptfoo skill-eval docs: https://www.promptfoo.dev/docs/guides/test-agent-skills/
- Promptfoo agent skill docs: https://www.promptfoo.dev/docs/integrations/agent-skill/
- DeepEval agent evaluation docs: https://deepeval.com/guides/guides-ai-agent-evaluation

## Conflicts And Constraints

1. **Workshop simplicity is authoritative.** `CLAUDE.md` says this repo is a teaching vehicle, not a production system; keep the full `agent/` source tiny and avoid extra abstractions/dependencies. That argues against adding Promptfoo, DeepEval, Pixie, LangSmith, or Datadog to this repo as part of the workshop material.
2. **The pyramid intentionally includes mocked/stubbed Level 1 tests.** Any adopted skill must distinguish “deterministic unit tests” from “end-to-end evals.” A skill that says “never mock the LLM” is unsuitable as the top-level default for this practice.
3. **Framework choice should follow app shape and adoption context.** Promptfoo is better for declarative prompt/RAG/agent regression suites and model comparison. DeepEval is better for Python-first pytest/tracing/agent metrics. LangSmith/Datadog are better when those platforms are already the trace/eval substrate.
4. **Human review must stay first-class.** The repo’s Level 4 driver is not a weakness; it encodes the principle that some signals remain expensive, subjective, and manual.
5. **Existing local/global skills do not currently include Promptfoo or DeepEval.** `npx skills list` showed no project-level skills and the global list did not include `promptfoo-evals` or `deepeval`.

## Recommendation

### Direct answer

Do **not** build a full eval-framework skill from scratch, and do **not** retrofit this workshop repo around a third-party eval framework.

The follow-up KB and online research strengthens, rather than weakens, the original recommendation. In practice, teams do use pyramid-like layered testing for AI agents, but they do not use one fixed layer taxonomy. The reusable value is therefore a routing discipline: decide which layer provides the cheapest credible signal for the failure mode, then choose the local/native or framework substrate that fits.

**Decision update — 2026-06-05:** Do not create the skill yet. First apply the testing pyramid in a future project that genuinely requires multiple AI validation layers, flesh out the testing required for that project, and only then extract the proven practice into a reusable skill.

Instead:

1. **Keep the workshop repo’s native pytest pyramid as the canonical teaching example.** It is simpler, clearer, and better aligned with the workshop constraint than any external eval framework.
2. **Adopt existing framework-specific skills when implementing real eval suites elsewhere:**
   - Use `promptfoo/promptfoo@promptfoo-evals` when the job is declarative prompt/agent/RAG evaluation, model comparison, CI eval output, red-team-adjacent eval setup, or evaluating agent skills themselves.
   - Use `confident-ai/deepeval@deepeval` when the job is a Python LLM app needing committed pytest evals, golden datasets, traces, and agent-level metrics.
3. **Defer the thin meta-skill until the practice is proven in a concrete project.** When that happens, the meta-skill should encode the AI app testing pyramid decision tree and route to pytest/native tests, Promptfoo, DeepEval, LangSmith, Datadog, or human-review packet generation. It should not duplicate framework documentation.

### Why a thin meta-skill is worth considering

A new skill is worth building if the goal is to preserve and repeat the *practice* learned here, not to replace existing tools. The durable practice is:

- test deterministic orchestration at the base,
- constrain real model tests with pinned settings and controlled fixtures,
- replay changing external context before judging semantics,
- run objective checks before LLM judges,
- calibrate judges with humans,
- reserve human review for subjective/high-stakes signals,
- choose eval tools based on app shape and failure mode.

Existing skills are strong at implementation once a tool is chosen. They are weaker as a neutral decision layer for “what layer of the pyramid should I add next?” A small router skill would fill that gap.

### Proposed meta-skill shape

Name options:

- `ai-app-testing-pyramid`
- `llm-testing-pyramid`
- `ai-eval-strategy`

Trigger examples:

- “add tests/evals for this AI app”
- “apply the AI testing pyramid”
- “how should we test this agent?”
- “do we need deterministic tests, evals, judges, or human review?”
- “turn this AI behavior into validation gates”

Workflow:

1. Inspect app shape: prompt-only, RAG, tool-using agent, multi-turn chatbot, coding/browser agent, production system.
2. Identify failure modes: schema/format, orchestration/tool calls, grounding/citations, semantic usefulness, safety/compliance, cost/latency, subjective quality.
3. Choose the lowest reliable validation layer:
   - deterministic code checks first,
   - constrained model tests when prompt/model behavior matters,
   - replay fixtures when external context is variable,
   - LLM judge only for semantic/qualitative claims,
   - human review for subjective, expert, safety, or preference signals.
4. Decide substrate:
   - native pytest for tiny Python apps/workshops,
   - Promptfoo for prompt/RAG/agent eval matrices and skill evals,
   - DeepEval for Python pytest/tracing/agent metrics,
   - LangSmith/Datadog when those trace platforms are already adopted,
   - custom human packet when the top-layer signal is required.
5. Output a small plan with commands, env requirements, cost/CI policy, and stop rules.

Anti-goals:

- Do not force a single framework.
- Do not add heavy dependencies to teaching repos by default.
- Do not replace Level 1 unit tests with live LLM evals.
- Do not treat LLM judges as ground truth.
- Do not run live evals in default CI unless explicitly approved.

## Assumptions

- The user expects this practice to be reused across projects, not only preserved in this one repo.
- Pi-compatible skills can be installed later if approved, but no install should happen as part of this research packet without explicit confirmation.
- The workshop repo should remain dependency-light and easy for attendees to read end-to-end.

## Decision Status

- **Resolved:** Do not draft or install a personal/global AI test pyramid skill now.
- **Resolved:** Keep Promptfoo and DeepEval as optional future implementation backends, not global installs by default.
- **Future trigger:** Revisit skill creation when working on a project that actually requires these validation layers. The sequence should be: define the project’s testing needs, apply the testing pyramid in practice, then extract a skill from the working pattern.
- **Still optional:** Decide later whether to promote this research into `docs/solutions/` as durable learning.

## Suggested Planning Prompt

Use this research packet and the CE brainstorm requirements doc to decide the implementation shape of an `ai-app-testing-pyramid` skill. The skill should encode the adaptive pyramid practice from the research-summarizer workshop plus actual-practice follow-up, then route to existing eval/testing skills or native implementation depending on app shape, failure mode, evidence source, and repo constraints. It should preserve workshop simplicity, distinguish deterministic tests from evals, prefer deterministic checks before LLM judges, adapt beyond the workshop’s exact four levels when replay/scenario/observability layers fit better, and keep human evaluation explicit.

## Research Summary

**Packet:** `docs/research/2026-06-04-ai-app-testing-pyramid-skill-options-research.md`

**Project-memory findings:** Strong. The repo already demonstrates the four-level pyramid with native pytest files and a Level 3 stabilization learning doc.

**External findings:** Strong. Anthropic, Datadog, Block, Promptfoo, OpenAI, DeepEval, Toucan, LangChain survey data, and practitioner repo writeups all support layered validation with deterministic checks, model-graded evals, trace/replay discipline, observability, and human calibration/review. The evidence supports the pyramid as an adaptive cost/confidence model, not one exact taxonomy.

**Main risks/questions:** Avoid overfitting a skill to one workshop repo; avoid replacing simple pytest teaching material with heavy frameworks; distinguish unit tests from end-to-end evals; decide where a meta-skill should live.

**Recommended next step:** Stop at the research/requirements/HTML review artifacts for now. Reopen the skill idea only after applying the testing pyramid in a concrete project that requires those layers.
