# Client 0 — LLM Candidate Generator Preview

## Overview

This document describes the **candidate generator port** introduced in WP-036.
It enables the commercial intake engine (WP-035) to produce draft replies using
a pluggable LLM backend, while keeping all execution fully offline and
simulation-only.

## Port contract

The generator is exposed as a small, replaceable interface:

```python
class CandidateGenerator(Protocol):
    def generate(self, event: CommercialIntakeEvent) -> CandidateReply: ...
```

Two implementations ship with the module:

| Implementation | Network? | Use case |
|---|---|---|
| `StaticCandidateGenerator` | No | Demos, tests, deterministic fallback |
| `OllamaCandidateGenerator` | Loopback only | Local Ollama when explicitly configured |

### `evaluate_intake(event, generator) → IntakeDecision`

High-level function that:
1. Calls `generator.generate(event)` to obtain a candidate reply.
2. Passes the candidate to `process_commercial_intake()` (WP-035 guard).
3. On any generation failure, returns a safe fallback decision with
   `needs_human_review=True`, `can_send=False`, `simulation_only=True`,
   and `provider_unavailable` flag.

The guard is **always** executed.  The LLM candidate never authorises,
prices, approves, or triggers external actions.

## Fully offline execution

All tests and demos run without any network connection:

- Tests use `httpx.MockTransport` — no sockets are opened.
- The demo script uses `StaticCandidateGenerator` exclusively.
- No Ollama instance, model download, or external API call is required.

```bash
# Run tests
uv run pytest -q tests/test_intake_candidate_generator.py

# Run demo
uv run python scripts/demo_intake_candidate_generator.py
```

## Requirements for local Ollama use

To use `OllamaCandidateGenerator` in a development environment:

1. Install Ollama locally and pull a model (e.g., `qwen3:8b`).
2. Ensure Ollama listens on loopback only:
   `http://127.0.0.1:11434` or `http://localhost:11434`.
3. Construct the generator with an injected `httpx.Client`:

```python
import httpx
from app.services.intake_candidate_generator import OllamaCandidateGenerator

client = httpx.Client(follow_redirects=False)
gen = OllamaCandidateGenerator(
    client=client,
    model="qwen3:8b",
    base_url="http://127.0.0.1:11434",
)
```

### URL safety

The constructor **rejects** any base URL that:
- Does not resolve to a loopback address (127.0.0.1, localhost, ::1).
- Contains embedded credentials (user:pass@).
- Contains query strings or fragments.
- Points to a public or private non-loopback IP.

This prevents accidental exposure to external services.

## Candidate vs. authorisation

**Critical distinction:** the LLM produces a *text candidate* (draft reply).
It does **not** decide:
- Whether a message may be sent (`can_send` is always `False`).
- Pricing, deadlines, or guarantees.
- Channel selection or approval workflows.
- Any external action.

All policy decisions are made by `process_commercial_intake()` in the WP-035
guard, which runs regardless of whether a candidate was produced.

## Risks

| Risk | Mitigation |
|---|---|
| Prompt injection via client text | Guard detects injection patterns and flags `possible_prompt_injection` |
| LLM invents prices or deadlines | System prompt forbids it; guard flags `financial_commitment_request` |
| Ollama service unavailable | `evaluate_intake` catches failure and returns safe fallback |
| Response body too large | 64 KiB guard rejects oversized responses |
| Redirect to external host | `follow_redirects=False`; non-2xx status raises error |
| Sensitive data in error messages | `CandidateGenerationError` messages are sanitised |
| Model name from client input | Model is fixed at constructor time, never from event |

## Future paths

1. **n8n internal channel** — Connect generated candidates to an internal
   n8n workflow with authentication, deduplication, rate limits, and human
   review before any external message is sent.  Requires separate authorisation.

2. **External providers** — Support for OpenRouter, DeepSeek, or other
   external LLM providers is **explicitly out of scope** for this package.
  Any external provider integration requires specific cost approval and a
   dedicated work package.

3. **Persistent deduplication** — The current implementation has no
   idempotency layer.  Repeating `evaluate_intake` after a failure may
   create duplicate candidate attempts.  A persistent deduplication
   mechanism is a future concern.

## Files

| File | Purpose |
|---|---|
| `app/services/intake_candidate_generator.py` | Generator port, static and Ollama implementations |
| `tests/test_intake_candidate_generator.py` | Full test suite with mock transport |
| `scripts/demo_intake_candidate_generator.py` | Offline demo with three scenarios |
| `docs/operations/client0-llm-preview.md` | This document |
