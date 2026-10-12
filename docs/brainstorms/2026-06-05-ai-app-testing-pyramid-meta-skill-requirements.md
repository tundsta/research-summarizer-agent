---
date: 2026-06-05
updated: 2026-06-05
topic: ai-app-testing-pyramid-meta-skill
source: ce-brainstorm
research_packet: docs/research/2026-06-04-ai-app-testing-pyramid-skill-options-research.md
linear_issue: BVA-480
---

# AI App Testing Pyramid Meta-Skill Requirements

## Summary

When the practice has been proven in a concrete project, create a personal/global meta-skill that helps choose the right validation layer for AI applications, then routes to the simplest suitable implementation path: native project tests, existing eval-framework skills, observability-backed eval workflows, or explicit human review.

---

## Problem Frame

The research-summarizer workshop produced a useful testing discipline for AI applications: deterministic orchestration tests at the base, constrained model tests above that, LLM-as-judge evals for semantic quality, and human evaluation for expensive subjective signals. That practice is valuable beyond this repo, but the reusable value is the decision discipline, not a new eval framework.

Existing shared skills are strong once a framework is chosen. Promptfoo, DeepEval, LangSmith, and Datadog-oriented skills each cover a specific substrate. The gap is earlier: when starting from “how should I test this AI app?”, the agent needs to inspect the app shape, identify failure modes, pick the lowest reliable validation layer, and avoid overbuilding.

Follow-up KB-first and online research confirmed that pyramid-like AI/agent testing is used in practice, but not as one canonical taxonomy. Block, Toucan, Anthropic, LangChain survey data, and practitioner repo writeups converge on layered cost/confidence trade-offs: deterministic tests, replay or fake-model integration, scenario/eval datasets, trace/observability workflows, LLM-as-judge where useful, and human review where necessary. Therefore the skill should preserve the adaptive decision discipline, not freeze the workshop’s exact four levels as universal.

Decision update — 2026-06-05: do not create the skill immediately. First apply the testing pyramid to a future project that genuinely needs these validation layers, flesh out and run the tests in context, then extract the working pattern into a skill.

---

## Actors

- A1. Personal skill user: Wants a repeatable way to decide how to validate AI app behavior across projects.
- A2. Coding agent: Uses the meta-skill to inspect context, ask only necessary clarifying questions, and produce a validation plan or handoff.
- A3. Framework-specific skill: Existing Promptfoo, DeepEval, LangSmith, Datadog, or similar skill that may be invoked after the meta-skill chooses a substrate.
- A4. Human reviewer: Provides judgment for subjective, high-stakes, expert, preference, or safety/compliance signals.

---

## Key Flows

- F1. Classify a validation request
  - **Trigger:** A user asks how to test, evaluate, add QA, or create evals for an AI app or agent.
  - **Actors:** A1, A2
  - **Steps:** The agent inspects project context, identifies app shape, identifies likely failure modes, and chooses the lowest validation layer that can provide credible signal.
  - **Outcome:** The user receives a small validation strategy instead of a premature framework install or generic eval advice.
  - **Covered by:** R1, R2, R3, R4, R16

- F2. Route to an implementation substrate
  - **Trigger:** The validation strategy points to a concrete implementation path.
  - **Actors:** A1, A2, A3, A4
  - **Steps:** The meta-skill recommends native tests, a framework-specific skill, an observability-backed workflow, or a human-review artifact, while preserving explicit constraints and non-goals.
  - **Outcome:** Downstream work starts from a scoped handoff with the right tool for the failure mode.
  - **Covered by:** R5, R6, R7, R8, R9

---

## Requirements

**Decision discipline**

- R1. The skill must start by distinguishing app shape: prompt-only LLM app, RAG/search app, tool-using agent, multi-turn chatbot, coding/browser agent, or production trace-backed system.
- R2. The skill must identify the failure modes that matter before proposing tools, including schema/format failures, orchestration/tool-call failures, grounding/citation failures, semantic usefulness, safety/compliance, cost/latency, and subjective quality.
- R3. The skill must choose the lowest reliable validation layer: deterministic checks first, constrained model tests when model behavior matters, replay fixtures when external context varies, LLM judges only for semantic/qualitative claims, and human review for subjective or high-stakes signals.
- R4. The skill must separate unit tests from evals. It must not adopt a blanket “never mock the LLM” rule because deterministic base-layer tests intentionally mock or stub external/model boundaries.

**Routing and handoff**

- R5. The skill must recommend native project tests for small, dependency-light, workshop-style, or pytest-first apps when that is clearer than adding a framework.
- R6. The skill must route to Promptfoo-style evals when the need is declarative prompt/agent/RAG evaluation, model comparison, CI-friendly eval output, grounded rubrics, or skill evaluation.
- R7. The skill must route to DeepEval-style workflows when the need is Python-first committed eval suites, golden datasets, tracing, or agent reasoning/action/execution metrics.
- R8. The skill must route to LangSmith, Datadog, or another observability-backed workflow only when that substrate is already chosen or production traces are the primary evidence source.
- R9. The skill must preserve human review as a first-class option rather than treating LLM-as-judge as a replacement for expert, preference, safety, compliance, taste, or domain-fit judgment.

**Output shape**

- R10. The default output must be a compact validation plan: app shape, risks/failure modes, recommended pyramid layers, proposed substrate, commands or next-step handoff, required environment variables or credentials, and CI/cost guidance.
- R11. The skill must explicitly call out what is not being done, especially when it declines to install a framework, declines to run live evals in default CI, or defers human review.
- R12. The skill must keep framework-specific details shallow unless the user asks to proceed into that framework’s skill. The meta-skill should route; it should not duplicate Promptfoo, DeepEval, LangSmith, or Datadog documentation.

**Personal/global scope**

- R13. Version 1 should optimize for the personal global workflow rather than team packaging, marketplace distribution, or this workshop repo as the only audience.
- R14. The skill should be useful even when framework-specific skills are not installed: it can recommend install commands or native alternatives without failing the strategy step.

**Interaction behavior**

- R15. When clarification is needed, the skill must ask one focused question at a time using the available blocking user-input tool, with `ask_user` as the Pi default.

**Evidence grounding**

- R16. The skill must treat the pyramid as an adaptive cost/confidence model rather than a fixed universal taxonomy. It may use the workshop’s four levels as a reference example, but it should adapt layers to the app shape and evidence source, including replay, scenario simulation, observability, or adversarial testing when those are the credible signal.

---

## Acceptance Examples

- AE1. **Covers R1, R2, R3, R5.** Given a tiny Python research summarizer with a clean dependency-injection seam, when the user asks for AI app testing guidance, the skill recommends native pytest layers before any external eval framework.
- AE2. **Covers R3, R4.** Given a request for fast tests of agent orchestration, when the failure mode is validation, tool routing, or error handling, the skill recommends deterministic stubs/mocks and does not dismiss that layer as a tautological eval.
- AE3. **Covers R6, R12.** Given a prompt or RAG app that needs a CI-friendly matrix of inputs, JSON assertions, grounded rubrics, and model comparison, when Promptfoo is appropriate, the skill routes to a Promptfoo skill instead of hand-writing a full Promptfoo tutorial.
- AE4. **Covers R7, R12.** Given a Python agent that needs traced reasoning/action metrics and committed pytest eval suites, when DeepEval is appropriate, the skill routes to a DeepEval workflow and leaves detailed instrumentation choices to that skill.
- AE5. **Covers R8, R9.** Given a production AI app with existing trace data and subjective quality complaints, when traces and human judgment are the primary evidence, the skill recommends an observability-backed eval/review workflow rather than only offline test cases.
- AE6. **Covers R9, R11.** Given a high-stakes or taste-heavy output, when an LLM judge could provide partial signal, the skill still calls out where expert human review is required or should calibrate the judge.
- AE7. **Covers R15.** Given missing context about app shape, eval substrate, or cost tolerance, when the skill needs clarification, it asks one focused `ask_user` question rather than bundling several questions into chat.
- AE8. **Covers R16.** Given a production agent with trace data and multi-turn workflows, when the workshop four-level taxonomy is too narrow, the skill adapts the plan to include replay/scenario/observability layers instead of forcing the exact workshop labels.

---

## Success Criteria

- The user can ask “how should I test/evaluate this AI app?” in any repo and receive a right-sized validation strategy in one pass.
- The skill prevents the two main failure modes: adding a heavy eval framework to a tiny app too early, or relying only on deterministic tests where semantic/model behavior is the risk.
- Downstream agents receive enough context to implement the chosen validation layer without inventing product behavior, scope boundaries, or evaluation intent.
- The practice learned from the workshop repo is preserved without turning the workshop repo into a framework showcase.

---

## Scope Boundaries

- Do not build a new eval framework.
- Do not replace existing Promptfoo, DeepEval, LangSmith, Datadog, or similar skills.
- Do not install framework-specific skills by default.
- Do not retrofit the workshop repo around third-party tooling.
- Do not run live LLM evals in default CI unless the user explicitly approves that cost/flakiness trade-off.
- Do not attempt a team-shared or marketplace-quality package in v1.
- Do not create v1 until a concrete project has exercised these testing layers in practice.

---

## Key Decisions

- Personal/global v1: The first version optimizes for the user’s own cross-project workflow, not team distribution.
- Router over framework: The skill preserves the testing-pyramid decision discipline and delegates framework-specific execution.
- Native tests remain valid: Deterministic base-layer tests intentionally use stubs/mocks; eval-only rules must not erase unit-test discipline.
- Human judgment remains explicit: LLM judges are useful but must be calibrated and bounded by human review where stakes or subjectivity require it.
- Clarification stays interactive: The skill asks one focused blocking question when context is missing instead of burying multi-part questions in chat.
- Actual practice is adaptive: Public examples and local KB research support the pyramid as a layered cost/confidence model, not one exact taxonomy.
- Implementation is deferred: create the skill later only after applying the pyramid in a project that requires these levels of testing.

---

## Dependencies / Assumptions

- The research packet, including the actual-practice follow-up, remains the evidence base for the first draft.
- Existing framework-specific skills can be installed later if the user chooses, but the meta-skill should not require them to produce a useful strategy.
- The user’s global skill directory is the likely home for v1, but the exact path and installation mechanism should be settled during planning or implementation.
- The current workshop repo remains a reference example, not the installation target for the personal skill.

---

## Outstanding Questions

### Deferred Until a Concrete Project Needs It

- [Technical] Decide the exact global skill name, file location, and install/update mechanism after a project has exercised the practice.
- [Needs project context] Decide whether Promptfoo, DeepEval, trace-platform workflows, or native tests are the right substrate based on the future project’s actual failure modes.
- [Technical] Decide whether to include a small example output template in the skill resources or keep everything in `SKILL.md` once the working pattern is known.
- [Needs validation] Test the eventual meta-skill against positive and negative prompts derived from the real project experience, not just abstract examples.
