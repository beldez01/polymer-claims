# Audit Hardening — Tier A + B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.
> Source: external audit `/Users/zbb2/Desktop/polymer-claims-audit.md` (2026-06-05). Tier A = cheap technical fixes; Tier B = docs/legibility. LOCAL ONLY, no push/publish.

**Goal:** Harden the live local node + tidy the CLI/contract seams + make the repo legible (current-state docs, quickstart, glossary, v1.2 frozen banners) — WITHOUT touching the verified grammar/protocol *logic* (one additive export-only protocol edit is allowed). Corpus stays 4 collections.

**Scope fence:** changes live in the umbrella `src/polymer_claims/`, `viewer/` (scripts/config/docs only — NOT the verified scene/interpolation), repo-root docs, and `v1.2/` doc banners. The ONE protocol edit is promoting two private helpers to public names (`timeline.py` + `__init__.py`, additive). NO grammar logic change, NO new Corpus collection, NO new protocol behavior.

**Decisions (locked):**
- v1.2 plugin → **banner as legacy-active** (keep installable; clear "v1.2/frozen — does NOT exercise the v1.3 runtime" labels).
- Non-loopback bind → **hard-refuse** unless `--unsafe-remote-control` passed.
- `--max-frames` default **10000**, drop-oldest ring; bounded SSE subscriber queues drop-oldest.
- `/step` `/pause` `/resume` `/` `/state` → `async def` + a single `asyncio.Lock` guarding `_do_tick` and state reads.
- CLI: human summaries → **stderr**, JSON → **stdout**.
- `#11` → promote `_frame_stats`/`_n_licensed` to public `frame_stats`/`n_licensed` (keep private aliases for back-compat).

**Verify (each task):** root `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q`; protocol unaffected `cd protocol && uv run pytest -q`; grammar isolation `cd grammar && uv run pytest tests/test_isolation.py -q`; viewer `cd viewer && npx tsc --noEmit && npm run build`. ABSOLUTE paths.

---

## Branch A — `feat/audit-hardening-tier-ab`

### Task 1: NodeRunner bounded retention (#3, node-side)

**Files:** `src/polymer_claims/node.py`; Test `tests/test_node.py`.

- [ ] **Step 1 — failing test:** a runner built with `max_frames=5` ticked 20× retains ≤5 frames, `frame_index`/`snapshot().n_cycles` still report the true total (20), warm-start positions stay stable, and the retained window is the NEWEST frames (last cycle_index == 20).
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement:** add `max_frames: int | None = 10000` to `__init__`/`from_seed`. Keep `self.frames` a list but trim from the front after each append when `len > max_frames` (or use `collections.deque(maxlen=...)` — but `snapshot()` must still `tuple(self.frames)` and frame 0 may be dropped). `frame_index` stays the monotonic true counter; `prev_positions` is unchanged (warm-start unaffected). `snapshot().n_cycles` stays `self.frame_index`. `max_frames=None` → unbounded (old behavior; the existing tests pass unchanged).
- [ ] **Step 4 — green** (root + protocol unaffected + ruff).
- [ ] **Step 5 — commit** `feat(node): bounded frame retention (--max-frames ring)`.

### Task 2: Server concurrency lock + bounded SSE queues + async mutators (#2, #3 server-side)

**Files:** `src/polymer_claims/server.py`; Test `tests/test_server.py`.

- [ ] **Step 1 — failing test:** (a) 30 concurrent `POST /step` calls (via `httpx.AsyncClient`/threads against `TestClient`) yield strictly-increasing, gap-free `frame_index` with no duplicates; (b) a subscriber queue created with a small bound drops oldest rather than growing unboundedly (assert the bounded-put helper caps size). If concurrent-TestClient is awkward, assert the lock serializes by checking `_do_tick` is wrapped and N sequential `/step` produce N gap-free indices PLUS a direct unit test of the bounded-queue put.
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement:** add `lock = asyncio.Lock()` in `create_app`; make `_do_tick` async (`async def _do_tick(): async with lock: frame = runner.tick(); _publish(frame); return frame`); make `root/state/step/pause/resume` `async def` and `await _do_tick()` where they tick; the background ticker `await _do_tick()` too. Bound each subscriber queue: `asyncio.Queue(maxsize=...)` with a `_publish` that, on `QueueFull`, drops the oldest (`get_nowait()` then `put_nowait`) — a small `_bounded_put(q, payload)` helper. Default subscriber bound e.g. 1000. Keep the on-connect current frame + heartbeat.
- [ ] **Step 4 — green** (server tests).
- [ ] **Step 5 — commit** `feat(server): asyncio.Lock tick serialization + bounded SSE queues`.

### Task 3: CLI bind guard + `--max-frames` wiring + machine-clean JSON (#1, #3, #9)

**Files:** `src/polymer_claims/cli.py`; Test `tests/test_serve_cli.py`, `tests/test_cli.py`.

- [ ] **Step 1 — failing tests:** (a) `serve --host 0.0.0.0` WITHOUT `--unsafe-remote-control` returns non-zero + a stderr hint; WITH the flag it proceeds (monkeypatch `_import_server` to a no-op as the existing serve tests do). (b) `run-cycle <corpus> ` (no `--out`) writes ONLY valid JSON to stdout (parseable as a `Corpus`); the human summary (`status:`/`frontier:`) goes to stderr. Same for `export-timeline` (frame-count line → stderr, JSON → stdout) and `loop` (trace/summary → stderr; final corpus JSON → stdout).
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement:** add `--unsafe-remote-control` (store_true) + `--max-frames` (int, default 10000) to the `serve` subparser; in `_cmd_serve`, if `args.host` not in `{"127.0.0.1","localhost","::1"}` and not `args.unsafe_remote_control` → `print(..., file=sys.stderr); return 1`; thread `max_frames=args.max_frames` into `from_seed`. For JSON cleanliness, route every human summary `print(...)` in `_cmd_run_cycle`/`_cmd_export_timeline`/`_cmd_loop` to `file=sys.stderr`, leaving `_write_or_print` (the JSON) on stdout when `--out` is omitted. (`version`/`validate`/`export-topology` already clean.)
- [ ] **Step 4 — green** (CLI tests + the install smoke `scripts/build_and_test_install.sh` still passes).
- [ ] **Step 5 — commit** `feat(cli): non-loopback bind guard + --max-frames + machine-clean JSON (stderr summaries)`.

### Task 4: Promote protocol frame-stat helpers to public (#11)

**Files:** `protocol/src/polymer_protocol/timeline.py`, `protocol/src/polymer_protocol/__init__.py`; `src/polymer_claims/node.py`; Test `protocol/tests/test_timeline.py`.

- [ ] **Step 1 — failing test:** `from polymer_protocol import frame_stats, n_licensed` imports cleanly and they produce the same values as before (a small equivalence test). 
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement:** in `timeline.py`, rename `_frame_stats`→`frame_stats` and `_n_licensed`→`n_licensed` as the public names, keep `_frame_stats = frame_stats` / `_n_licensed = n_licensed` aliases (so internal callers + back-compat hold). Add both to `__init__.py` `__all__` + imports. Update `src/polymer_claims/node.py` to import the PUBLIC names. ADDITIVE, no logic change — protocol behavior byte-identical.
- [ ] **Step 4 — green** (protocol full suite + root + isolation both ways).
- [ ] **Step 5 — commit** `refactor(protocol): promote frame_stats/n_licensed to public API`.

### Task 5: Viewer verification scripts + local check-all (#18, #8-local)

**Files:** `viewer/package.json`; new `scripts/check-all.sh`; Test: n/a (scripts).

- [ ] **Step 1 — implement viewer scripts:** add `"typecheck": "tsc --noEmit"` and `"lint": "next lint"` (or `eslint .` if next lint absent) to `viewer/package.json` `scripts`. Verify both run: `cd /Users/zbb2/Desktop/polymer-claims/viewer && npm run typecheck` (clean) and `npm run lint` (clean or pre-existing-only warnings — do NOT mass-fix lint here; just wire the script).
- [ ] **Step 2 — implement `scripts/check-all.sh`** (substitute for flag-blocked CI): a bash script that runs, with clear section headers + non-zero exit on any failure: root pytest+ruff, grammar pytest+ruff+isolation, protocol pytest+ruff, viewer `npm run typecheck` + `npm run build`. Use ABSOLUTE paths. `chmod +x`.
- [ ] **Step 3 — run it** end-to-end; confirm all green.
- [ ] **Step 4 — commit** `chore: viewer typecheck/lint scripts + local check-all.sh (CI substitute)`.

**After 1–5 reviewed:** finish Branch A in ONE branch (these are sequential, same branch). Merge local no-ff, no push — AFTER Branch B docs (below) land on the same branch so it's one coherent hardening merge. (Docs are doc-only; keep them on the same branch.)

---

## Branch A (continued) — Tier B docs (same branch)

### Task 6: Current-architecture doc + glossary (#6, #21)

**Files:** new `ARCHITECTURE_CURRENT.md`, new `GLOSSARY.md` (repo root).

- [ ] **Step 1 — `ARCHITECTURE_CURRENT.md`:** a SHORT (~1 page) current-truth map. Three buckets: **Active** (v1.3 `grammar/` IR + `protocol/` runtime + `src/polymer_claims/` umbrella node/CLI/server + `viewer/`), **Frozen** (`v1.2/` package/corpus/plugin — fallback, does NOT exercise v1.3), **User-gated/future** (PyPI publish [flagged account → local token only], PolymerGenomicsAPI/polymerbio.org integration, public-corpus revival, adapter trust registry). One line each on how the active pieces connect (grammar=what a claim is → protocol=how a corpus evolves → node=local host → viewer=renders the topology). Point to `docs/superpowers/CONTINUE.md` as the detailed continuity log (do NOT duplicate it).
- [ ] **Step 2 — `GLOSSARY.md`:** terse definitions reserving each term: FormalClaim (v1.2 only), grammar (v1.3 IR), protocol (runtime/flywheel), corpus, claim, node (local mutable host), topology/timeline (export DTOs), viewer (standalone Next/Three.js UI), run_cycle, licensing/air-gap, daemon, scheduler/next_action, oracle, representation-revision, polymerbio.org (the API site, integration target). 1–2 lines each.
- [ ] **Step 3 — commit** `docs: ARCHITECTURE_CURRENT + GLOSSARY (current-truth map)`.

### Task 7: README quickstart — live universe first (#19, #20)

**Files:** `README.md` (repo root — read it first; preserve the vision section, ADD the quickstart near the top).

- [ ] **Step 1 — implement:** add a "Run the live universe locally" quickstart as the first runnable path: two terminals — (1) `uv run --project . polymer-claims serve` (note `pip install -e '.[serve]'` / the `[serve]` extra), (2) `cd viewer && npm run dev` then open the viewer and Connect to `http://localhost:8000`. One paragraph: **sample mode** (loads `public/sample-timeline.json`) vs **live mode** (connects to a running node). Add a compact "fresh-clone dev" block: install/test/ruff/build commands for root+grammar+protocol+viewer + `scripts/build_and_test_install.sh` + `scripts/check-all.sh`. Keep it accurate to the actual commands.
- [ ] **Step 2 — verify** the commands are correct (cross-check against `cli.py` + `viewer/package.json`).
- [ ] **Step 3 — commit** `docs(readme): live-universe quickstart + fresh-clone dev commands`.

### Task 8: v1.2 frozen banners (#7, #16) — keep installable, label clearly

**Files:** `v1.2/README.md`, `v1.2/plugins/claim-harness/README.md` (+ any v1.2 corpus/plugin contribution doc that reads as active), `.claude-plugin/marketplace.json` (description only — keep the entry installable).

- [ ] **Step 1 — implement:** add a prominent top banner to the v1.2 plugin/corpus docs: **"⚠️ v1.2 — FROZEN FALLBACK. This authors/validates v1.2 FormalClaim drafts and does NOT exercise the v1.3 grammar/protocol runtime. The active path is the v1.3 local node (`polymer-claims serve`) + viewer."** Update the `claim-harness` entry's `description` in `marketplace.json` to say `(v1.2 / frozen — legacy authoring, not the v1.3 runtime)` — KEEP it installable (legacy-active policy). Do NOT change v1.2 code/behavior (audit findings #13–#15 about v1.2 evaluator semantics are policy-deferred, not fixed here — note them as known in `ARCHITECTURE_CURRENT.md`'s frozen bucket).
- [ ] **Step 2 — verify** marketplace.json still parses (valid JSON) and the entry still resolves to `./v1.2/plugins/claim-harness`.
- [ ] **Step 3 — commit** `docs(v1.2): frozen-legacy banners (keep installable, label clearly)`.

**After 6–8:** run `scripts/check-all.sh` once more; finish the branch (merge local no-ff, no push); update `docs/superpowers/CONTINUE.md` + memory; capture the deferred Tier-C items (adapter registry #5, schema→TS codegen #10, API faceting #12, v1.2 evaluator semantics #13–15) as tracked notes.

## Self-Review
- Scope: only umbrella/viewer-scripts/docs/v1.2-banners touched; the one protocol edit (Task 4) is export-only/additive; grammar logic + Corpus(4) untouched. ✓
- Audit coverage: #1(T3) #2(T2) #3(T1+T2+T3) #9(T3) #11(T4) #18(T5) #8-local(T5) #6(T6) #21(T6) #19(T7) #20(T7) #7(T8) #16(T8). Tier-C (#4,#5,#10,#12,#13–15,#17) explicitly deferred + tracked. ✓
- No placeholders: every task names files, the decision, the test. ✓
