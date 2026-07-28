# Parallel Agent Graph — Build Plan & Bill of Materials

**Architecture recap:** LangGraph (Python) with a Postgres checkpointer. One container image, two Cloud Run deployments — a request-scoped **service** (API) and a long-running **job** (graph execution). Gemini via Vertex AI with ADC (zero secrets). All triggers are thin adapters into one entrypoint; resume is just another request carrying a `thread_id`.

---

## Part 1 — Bill of Materials

### GCP resources

| # | Resource | Purpose / Notes |
|---|----------|-----------------|
| 1 | GCP project + enabled APIs | Cloud Run, Cloud SQL Admin, Pub/Sub, Cloud Scheduler, Vertex AI, Artifact Registry, Cloud Build |
| 2 | Artifact Registry repo | Container images |
| 3 | Cloud SQL (Postgres) instance | Smallest tier to start. One database (`agentgraph`). Checkpoints + action registry + dedup table live here |
| 4 | Cloud Run **service** `agent-api` | Start / resume / status endpoints. Returns `202` immediately. Ingress restricted, auth required |
| 5 | Cloud Run **job** `agent-runner` | Owns graph execution. Long task timeout (hours). Retries are safe — resume comes from checkpoints |
| 6 | Pub/Sub topic `runs.start` + push subscription | Event trigger path. Push sub authenticates to the service via OIDC |
| 7 | Cloud Scheduler job(s) | Batch trigger path — publishes to the topic |
| 8 | Service account `sa-agent-api` | Needs permission to execute the runner job + Cloud SQL Client |
| 9 | Service account `sa-agent-runner` | `roles/aiplatform.user` + Cloud SQL Client |
| 10 | Service account `sa-pubsub-push` | `roles/run.invoker` on the service |
| 11 | Cloud SQL connection from both Run deployments | Built-in Cloud SQL connector (unix socket) — simplest path |
| 12 | Cloud SQL auth choice | IAM database auth (zero passwords) **or** built-in user + Secret Manager. Decide once in Phase 0 |

### Software components (one repo, one image)

| # | Component | Notes |
|---|-----------|-------|
| 1 | Graph module | State schema with reducers, planner node, generic agent node, fan-in, review gate (`interrupt()`), finalize |
| 2 | Action registry | `action → prompt template, tools, model, params`. YAML v1; DB table later if runtime edits needed |
| 3 | Checkpointer | `langgraph-checkpoint-postgres` (`PostgresSaver`) + its `setup()` migration |
| 4 | Gemini client | `google-genai` SDK in Vertex mode — picks up ADC automatically |
| 5 | API app (FastAPI) | `POST /runs`, `GET /runs/{thread_id}`, `POST /runs/{thread_id}/resume`, Pub/Sub push handler |
| 6 | Runner entrypoint | Reads `thread_id` from job override, invokes graph, exits on `interrupt()` or completion |
| 7 | Idempotency layer | Dedup table keyed on Pub/Sub `messageId`; idempotency keys for side-effectful actions |
| 8 | Dockerfile + deploy scripts | Single image, entrypoint switch. `gcloud` scripts (Terraform optional, later) |
| 9 | Tests | Unit (reducer, registry, planner) + integration with `MemorySaver` (no infra needed) |
| 10 | Observability | Structured logs keyed by `thread_id`, log-based metrics, failure alert |
| 11 | Docs | "Add an action" guide + operational runbook |

---

## Part 2 — Todo List (phased; each phase has an exit test)

### Phase 0 — Foundations
- [ ] Pick one region for Run + SQL + Vertex (co-locate everything)
- [ ] Enable APIs; create Artifact Registry repo
- [ ] Create the three service accounts + IAM bindings
- [ ] Provision Cloud SQL, create database and user; decide IAM auth vs. password
- [ ] **Exit test:** `psql` connect works with the chosen auth path

### Phase 1 — Graph core (local, zero GCP dependencies)
- [ ] Repo scaffold (`pyproject`, src layout)
- [ ] State schema: results list with append reducer + merge-safe keys
- [ ] Action registry v1 (YAML) + loader + schema validation
- [ ] Generic agent node: dispatch through registry → Gemini call
- [ ] Planner node emitting one `Send()` per task
- [ ] Review gate (`interrupt()`) + finalize node; wire the graph
- [ ] Unit tests: reducer merge, registry validation, planner fan-out
- [ ] **Exit test:** full run with `MemorySaver` — fan-out, pause, resume via `Command(resume=...)` — passes locally

### Phase 2 — Durability
- [ ] Swap in `PostgresSaver` (local Postgres via docker-compose); run `setup()`
- [ ] Kill-and-resume test: crash mid-fan-out, re-invoke same `thread_id`, verify completion
- [ ] Confirm which work re-executes on resume; add idempotency keys to any side-effectful action
- [ ] **Exit test:** process death mid-run is provably a non-event

### Phase 3 — API service
- [ ] `POST /runs` → mint `thread_id`, persist intake, return `202`
- [ ] `GET /runs/{thread_id}` → status from checkpointer state snapshot
- [ ] `POST /runs/{thread_id}/resume` → `Command(resume=verdict)`
- [ ] Pub/Sub push handler: verify OIDC, unwrap envelope, dedup on `messageId`
- [ ] Service triggers a runner-job execution with `thread_id` passed as an override
- [ ] **Exit test:** all three endpoints work locally against docker-compose Postgres

### Phase 4 — Containerize + deploy
- [ ] Dockerfile (one image, `API_MODE`/args switch between server and runner)
- [ ] Deploy service: auth required, sensible concurrency, min instances 0
- [ ] Deploy job: long task timeout, small retry count (retries resume from checkpoint)
- [ ] Attach Cloud SQL to both; wire Scheduler → topic → push sub → service
- [ ] **Exit test:** `curl` with an identity token starts a real run end to end

### Phase 5 — Verification gate
- [ ] Interactive path: start → poll → resume → final state correct
- [ ] Event path: publish test message; redeliver it; verify dedup (exactly one run)
- [ ] Batch path: force-run the Scheduler job
- [ ] Chaos: kill the job execution mid-run; verify auto/manual resume
- [ ] Load: wide fan-out run; observe Gemini 429s; add backoff/concurrency cap in agent node
- [ ] Time: resume a run paused >24h
- [ ] **Exit test:** all six pass on deployed infra

### Phase 6 — Operations
- [ ] Structured logging with `thread_id` on every line; log-based metrics
- [ ] Alert policy on job execution failure
- [ ] Checkpoint retention: pruning policy for completed threads (checkpoints grow forever otherwise)
- [ ] Cloud SQL automated backups on
- [ ] Docs: add-an-action guide; runbook (stuck run, manual resume, replay)
- [ ] **Exit test:** a teammate can add a new action using only the guide

---

## Definition of done

1. All three trigger paths (HTTP, Pub/Sub, Scheduler) produce completed runs through the same entrypoint.
2. Killing the runner mid-run loses nothing — re-invocation resumes from the last checkpoint.
3. A run paused at the review gate resumes days later via one API call.
4. Adding a new agent capability requires **only** a registry entry — no graph changes, no deploy.
5. A failure anywhere pages you with a `thread_id` you can trace end to end in logs.