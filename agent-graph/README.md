# agent-graph

Parallel agent graph: LangGraph fan-out/fan-in, human-in-the-loop pause/resume,
durable checkpoints. Targets Cloud Run (service + job) with Cloud SQL Postgres
and Gemini via Vertex AI ADC. This snapshot is **Phase 1**: the graph core,
runnable entirely locally.

## Quickstart (Phase 1 exit test)

```bash
pip install -e ".[dev]"
pytest                                            # unit + e2e with in-memory saver
AGENT_GRAPH_FAKE_LLM=1 python scripts/run_local.py  # watch pause → resume happen
```

No GCP project, no credentials, no network needed — `AGENT_GRAPH_FAKE_LLM=1`
swaps in a deterministic fake at the LLM boundary.

## Layout

```
registry/actions.yaml     capability catalog: action → model, prompt, params
src/agent_graph/
  state.py                RunState; the reducer on `results` is the fan-in
  registry.py             load + validate the catalog (fails at load, not at run)
  llm.py                  Vertex ADC client + FakeLLM switch
  nodes.py                plan, fan_out (Send emitter), agent, review, finalize
  graph.py                wiring + compile
scripts/run_local.py      human-runnable exit test
tests/                    registry, planner, end-to-end pause/resume
```

## Phase map

- **Phase 1 (this):** graph core, local only ✅ when `pytest` and `run_local.py` pass
- **Phase 2:** swap `InMemorySaver` → `PostgresSaver`; kill-and-resume test
- **Phase 3:** FastAPI service (start / status / resume) + Pub/Sub handler
- **Phase 4:** containerize; deploy service + job; wire triggers
- **Phase 5–6:** verification gate; operations

See `agent-graph-build-plan.md` for the full checklist and BOM.
