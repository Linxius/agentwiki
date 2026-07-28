---
name: wiki-project-optimize
description: "Optimize this wiki project's workflows, reduce token consumption, and improve code quality. Use when user asks to '优化项目' / 'optimize project' / '减token' / '瘦身' / 'refactor', or when running health/lint finds many issues, or when user says '每次都要读很多文件' / '占用太多token'. Works with MiMoCode and OpenCode."
---

# Wiki Project Optimize

## Before you start

Read these docs first (they are concise):

1. `docs/architecture.md` — project architecture overview (~100 lines)
2. `docs/tools-reference.md` — tool quick reference (~80 lines)
3. `AGENTS.md` — full workflow spec (only after reading above)

## Optimization checklist

### Phase 1: Diagnostics (read-only, ~0 LLM tokens)

- [ ] Run `python tools/health.py` — structural check
- [ ] Run `python tools/status.py` — pipeline status
- [ ] Check `TODO.md` for existing optimization tasks
- [ ] Count AGENTS.md lines / estimate token size
- [ ] Check `raw/.tmp/` for stale files

Report results to user before proceeding.

### Phase 2: Token optimization (prioritized)

#### P0 — Externalize subagent prompts from AGENTS.md
Move large prompt templates out of AGENTS.md into `docs/workflows/*.md`:
- `docs/workflows/code-read.md` for the code-read subagent prompt (~200 lines)
- Reference as `→ See [code-read workflow](docs/workflows/code-read.md)` instead of inline

**Token saved**: ~2000-3000 per session

#### P1 — Externalize trigger tables from AGENTS.md
Move the large config/trigger tables out:
- `docs/workflows/triggers.md` for all trigger tables
- `docs/workflows/status-flow.md` for status flow description

**Token saved**: ~500-1000 per session

#### P2 — Remove redundant instructions from deep-read / ingest prompts
- Check if prompt templates inline schema that's already in shared context
- Check if `build_ingest_prompt` includes AGENTS.md fragments that can be removed
- Verify `get_shared_ingest_context()` is being used consistently

**Token saved**: ~1000-5000 per call

#### P3 — Caching and result reuse
- Verify deep-read dedup works correctly (title-based check)
- Verify brief.md content-hash dedup works
- Check if repeated `filter` runs reuse previous analysis

### Phase 3: Workflow optimization

- [ ] Batch subagents: are we spawning too many? (target 10-15 per batch)
- [ ] Compact previews: filter using only title+abstract (~2500 chars)?
- [ ] Source file reuse: are we re-fetching arxiv papers unnecessarily?
- [ ] Phase 1/2 protocol: any subagent writing sync issues?
- [ ] Parallelism opportunities: which steps can run in parallel?

### Phase 4: Code quality

- [ ] Stale/disused code: `call_llm()` calls that should be removed
- [ ] Inconsistent error handling across tools
- [ ] Missing `.gitignore` entries for temp files
- [ ] Unused imports or dead code branches

## Key decision framework

| If | Then |
|----|------|
| Same pattern repeated 3+ times | Script it |
| File > 500 lines and growing | Extract to `docs/` |
| Subagent count > 5 per task | Batch merge |
| Same file read in 3+ consecutive turns | Cache or reference by name |
| Step can be automated end-to-end | Write a pipeline script |

## References

- `docs/architecture.md` — architecture overview
- `docs/tools-reference.md` — tool reference
- `AGENTS.md` — full workflow specification
- `TODO.md` — known issues and pending work
- `token-optimization-plan.md` — detailed token savings plan
