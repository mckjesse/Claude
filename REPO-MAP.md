# REPO-MAP.md — the mckjesse git estate

Assessed 20 August 2026, last updated 21 August. Written because this repo's
branch layout was actively misleading and the reasoning behind the cleanup
should outlive the conversation that produced it.

**Scope.** This is a repository-and-branch tidy-up. Nothing in any
application has been modified — no code, no schema, no deploy settings beyond
the Render source repointing that the backend extraction required.

**Done:** Phases 0–4. Every branch tip archived; the deploy warning corrected;
CI added; the backend extracted to `CRM-backend` with Render cut over; the
frontends renamed; the six single-file tools consolidated into `foxd-apps`;
the tool inventory extracted to `foxd-tool-inventory`.

**Phase 5 done too, 21 Aug.** `main` is `Claude`'s default branch and the
thirteen superseded branches are deleted — 29 refs down to 17, of which 14
are the `archive/2026-08-20/*` safety net. The estate is tidy.

**How to work in it now:** see `WORKING-LOCALLY.md` — the `~/Developer`
layout, the branch-per-change workflow, and the three things that bite
(merging to `CRM-backend` `main` deploys; three repos are also written to by
Lovable's bot; `.env` files are deliberately not in git).

**Left at your discretion:** delete `CRM-Backend-snapshot-2026-04` and the
empty `FOXD`; make `foxd-apps` and `foxd-tool-inventory` private; retire
`claude/foxd-tender-backend-NiPeb` once you trust `CRM-backend`; and on `COD`,
set `main` as default and delete its old branch.

## The one-line summary

`mckjesse/Claude` used **branches as if they were repositories**: fourteen
branches, each an unrelated application, all descending from one root
commit. Everything else that was wrong followed from that — no `main` to be
the truth, so no merge target, so four pull requests closed unmerged and a
backend forked three ways; and a default branch pointing at the wrong app.

The fix is one repo per deployable thing. Two are out (`CRM-backend`,
`CRM-web`); the rest is Phases 3–5 below.

## Estate at a glance

| Repo | Vis. | Branches | What it is | Disposition |
|---|---|---|---|---|
| **`CRM-backend`** | private | `main` | **The Tender Pipeline API.** Extracted 21 Aug with the full 64-commit history, so every SHA in its `docs/DECISIONS.md` still resolves. Render builds production from `main`; CI gates it. **Since extraction it has grown an `apps/agent/` surface** — API-key auth, throttling, permissions, an approval workflow, an audit service and `create_agent_key`, with its own six test modules — and reached 68 commits, merged via pull request. | ✅ Done, and in active use |
| **`CRM-web`** | private | 1 (`main`) | The Lovable React frontend, renamed from `tender-tracker-pro`. Lovable's GitHub sync survived the rename — `lovable-dev[bot]` has pushed since. `.env` → `crm-backend-pza6.onrender.com` (dev/preview), `.env.production` → `api.foxd.co` (the deployed build). | ✅ Done |
| `Claude` | public | 17 | **This repo — now an archive.** `main` is the default and holds only a README, `REPO-MAP.md` and `WORKING-LOCALLY.md`. The fourteen app branches are gone; 14 `archive/2026-08-20/*` refs preserve every original tip, plus `claude/foxd-tender-backend-NiPeb` as the backend rollback path. Nothing is developed here. | ✅ Retired |
| **`foxd-apps`** | public | 1 (`main`) | **The six single-file fit-out tools**, consolidated 21 Aug 2026 — one directory per tool, each a self-contained HTML app, no build step. Netlify publishes the root verbatim. | ✅ Done — consider making private |
| **`foxd-website`** | private | 1 | The FOXD public marketing site and `/book` lead funnel, renamed from `foxd-4992dbd1`. | ✅ Done |
| ~~`foxd-hub-9c7dc867`~~ | — | — | **Deleted 21 Aug 2026.** Held React ports of the ceiling-grid and tender-scorecard tools. Those ports are gone; the HTML originals survive on their branches and in `archive/2026-08-20/*`, and are now in `foxd-apps`. GitHub keeps deleted repos restorable for a limited window if the React work is ever wanted back. | Deleted |
| `merrigums` | private | 1 | **Live site for `merrigums.com.au`** — the Merrijig holiday rental. Long-form single page with gallery lightbox, reviews, JSON-LD `LodgingBusiness` schema, and an Airbnb-synced availability calendar via a Supabase edge function. A separate business from FOXD. | Keep the name |
| **`foxd-tool-inventory`** | public | 1 (`main`) | **Plant and equipment tracking**, extracted 21 Aug from `claude/tool-inventory-app-7qfn6` with full history. Django + DRF + React, Entra ID auth. `Project` / `Tool` / `AllocationHistory`. | ✅ Done — consider making private |
| `COD` | public | 2 | Black Ops 7 randomizer. **`main` created 21 Aug** from `claude/bo7-game-mode-randomizer-wdccrm` (same commit). Set `main` as default, then delete the old branch. | Nearly done |
| **`CRM-agent`** | private | `main`, `feat/crm-agent-service` | **A specialist sub-agent for the CRM.** Reads and writes it *only* through the backend's controlled `/api/agent/` surface — no database access, no Django access, and it cannot approve its own consequential actions. 22 tools, and six test modules including safety, approvals and safe-writes. Python package `foxd_crm_agent`. | ✅ In git |
| **`foxd-ea`** — Ava | **not on GitHub** | — | **The Executive Assistant agent**, and the tier above `CRM-agent`. A Claude Code project: `CLAUDE.md`, `SETUP.md`, `context/`, four skills, `scripts/`, `state/`. **Local only — verified absent from GitHub on 22 Aug.** Lives at `C:\Dev\foxd-ea`. | ⚠️ Needs publishing |
| `CRM-Backend-snapshot-2026-04` | public | 1 | The former `CRM-Backend`, renamed 21 Aug to free the name. A single-commit orphan (`8f3b821`) sharing no history with anything — 3 migrations against production's 11. Its history exists **nowhere else**, which is why it was renamed rather than deleted. | Delete when ready |
| `FOXD` | public | 0 | Completely empty. A good name attached to nothing. | Repurpose or delete |

## The three critical findings — all resolved

Kept here because the reasoning matters, and because two of them were
recorded backwards in this codebase's own docs for months.

1. **~~Production deployed from a feature branch in a fourteen-app repo.~~
   RESOLVED 21 Aug 2026.** Render now builds `mckjesse/CRM-backend` @ `main`,
   with **Auto-Deploy `After CI Checks Pass`** — so CI is a real gate, not a
   smoke alarm. Before that it was `mckjesse/Claude` @
   `claude/foxd-tender-backend-NiPeb` with `On Commit`, meaning every push
   was an unreviewed production release; and because that repo's default
   branch was the Variation Register, a fresh clone landed on a different
   application entirely.

   `entrypoint.sh` still runs `migrate --noinput` on every deploy, so a
   deploy carrying a new migration still changes the production schema. That
   part is by design, not a defect — but it is why `makemigrations --check`
   is the first step in CI.

2. **~~One commit of production truth was stranded.~~ RESOLVED 20 Aug 2026.**
   The live branch's `CLAUDE.md` claimed *"Pushing here does NOT deploy...
   set to manual deploy"* while Render was set to `On Commit`. The commit
   correcting it, `c2e92d0`, sat for two days on an unrelated branch
   (`claude/chat-history-github-upload-ro7k35`) — one commit ahead of the
   branch that actually deployed. Fast-forwarded on 20 Aug after validating
   the merged state: 160 tests green, no migration drift, docs-only diff.

3. **~~No CI existed at all.~~ RESOLVED 21 Aug 2026.**
   `.github/workflows/backend-ci.yml` in `CRM-backend` runs what a deploy
   does, in order: `makemigrations --check`, `collectstatic` (which the
   Dockerfile does at build time, so a failure means no image), then the full
   suite on Python 3.12 against Postgres 16. First run passed in 63 seconds.

4. **~~The convincingly-named branch was the stale one.~~ RETIRED.**
   `CRM-Backend` looked like the integration branch and had three "Merge
   branch 'claude/foxd-tender-backend-NiPeb' into CRM-Backend" commits. That
   stopped 15 July 2026. It was strictly behind: missing migration
   `0011_opportunity_award_date`, the Mark Won workflow, the production-domain
   config, the terminal follow-up work and two test modules — plus 33
   committed `.pyc` files. Its schema never matched production.

## The backend forked three ways — now converged

```
BEFORE                                                          AFTER

CRM-Backend (repo) ─ 1 commit, unrelated history, 3 migrations → renamed
                                                                 CRM-Backend-
                                                                 snapshot-2026-04

                ┌── CRM-Backend branch — 10 migrations, no docs/ → retired
dde299c ─ cd66dfa ┤  (strictly behind; 33 .pyc committed)
 root    15 Jul   └── claude/foxd-tender-backend-NiPeb ─ c2e92d0 → retained as
                      11 migrations, CLAUDE.md + docs/             rollback only
                              │
                              └──► mckjesse/CRM-backend @ main  ★ LIVE
                                   64 commits, private, CI green
```

The standalone `CRM-Backend` **repository** shared no git history with the
branch of the same name — which is why renaming it, rather than deleting it,
was the safe move: commit `8f3b821` exists in no other repo.

## Branches in this repo

### Backend family — extracted 21 Aug 2026
All three are now dead weight in this repo; the code lives in
`mckjesse/CRM-backend`.

| Branch | Commits | Status | Action |
|---|---|---|---|
| `claude/foxd-tender-backend-NiPeb` | 63 | Was production until 21 Aug. Now at `c2e92d0`, identical to the extraction's parent commit. | **Keep until you trust the new repo**, then delete |
| `claude/chat-history-github-upload-ro7k35` | 63 | Identical SHA to the above. Carries nothing unique. | Delete |
| `CRM-Backend` | 73 | Strictly behind. Misleading name. | Delete |

### Tool inventory — three attempts at one app

Commit counts mislead badly here. `A6PBz` looks like the leader at 25
commits, but almost all of that history is an **inherited copy of the CRM
Django backend** that rode along when `Tool-tracker-app` branched off the
backend line. Measured by code that is actually a tool inventory, the
ranking inverts.

| Branch | Real app | What it actually is | Action |
|---|---|---|---|
| `claude/tool-inventory-app-7qfn6` | 1,969 ln | **Purpose-built and structurally the real one.** Django `inventory` app with a relational model — `Project`, `Tool` (typed, FK to project) and `AllocationHistory` recording action, from-location, to-location, performed-by. Entra ID JWT auth validated against Microsoft's JWKS. React frontend with Dashboard, Projects, ToolRegistry, Allocations, plus CSV import with duplicate detection. | **Recommended base** |
| `claude/tool-inventory-app-A6PBz` | 1,168 ln | Vanilla JS + HTML/CSS over a single 141-line Netlify function and a Netlify Blobs store — one JSON key holding everything, flat tools and projects, **no allocation history at all**. Has CSV import, but so does 7qfn6. The other 5,313 lines here are the stale CRM backend as baggage. | Harvest branding, then retire |
| `Tool-tracker-app` | — | **Zero unique commits** — strict subset of `A6PBz`. | Delete |

**Recommendation: build on `7qfn6`.** For tracking plant and equipment
across project sites the question that matters is *where is this tool now and
who moved it*, and only 7qfn6 models that. Its Entra ID auth also matches the
Microsoft 365 tenant already in use, so there is no separate login to
maintain. Carry over the FOXD logo and styling from `A6PBz`.

### Single-file tools — migrated to `foxd-apps` 21 Aug 2026

All six are now directories in `mckjesse/foxd-apps`. These branches carry
nothing unique and are ready to delete.

| Branch | The actual app | Now at |
|---|---|---|
| `claude/ceiling-grid-calculator-poae9` | `index.html` | `foxd-apps/ceiling-grid/` |
| `claude/sliding-door-calculator-BNpIe` | `sliding-door-calculator.html` | `foxd-apps/sliding-door/` |
| `claude/variation-register-app-oXKwO` | `index.html` — also the old repo's default branch | `foxd-apps/variation-register/` |
| `claude/quote-request-tracker-9sxkl` | `quote-tracker.html` | `foxd-apps/quote-tracker/` |
| `claude/parking-cost-tracker-8hfUy` | `parking.html` | `foxd-apps/parking/` |
| `claude/tender-scorecard-app-wD4lq` | `tender-scorecard.html` | `foxd-apps/tender-scorecard/` |

Two defects were fixed in the move. The `index.html` trap below is gone —
each tool's real file is now its own `index.html`. And
`variation-register`'s `logo.png` finally exists: that app had referenced it
since Feb 2026, but the file only ever entered git history on an unrelated
branch (`claude/tool-inventory-app-A6PBz`, commit `5908f3b`), so the logo had
always 404'd. It was copied across from there, which means its provenance is
the tool inventory's mark rather than one chosen for this app.

Also verified rather than assumed: **none of the six makes a network
request**; the two calculators persist nothing; the other four use
`localStorage` only.

### Superseded, nothing to migrate

| Branch | Why |
|---|---|
| `claude/tender-tracking-crm-oX0mN` | `tender-crm.html` — an early single-file sketch of what became `CRM-backend` + `CRM-web` |
| `claude/cod-team-randomizer-dvscjb` | The standalone `COD` repo's `index.html` is 1,591 lines and **already contains both wheels inline**, including the `meow` audio from this branch's final commit. It supersedes this branch's two separate pages (465 + 799 lines). `COD` still needs a `main`, but nothing needs moving into it. |

### The `index.html` trap

**Eleven of fourteen branches serve the wrong app at `index.html`.** The
Variation Register's `index.html` rode along from the root commit into
almost every branch. On `claude/parking-cost-tracker-8hfUy` the real app is
`parking.html`; on the COD branch it is `cod-team-wheel.html`. Anything that
serves a directory root — GitHub Pages, Netlify, any static host — shows the
wrong application by default.

## Where things should live

One principle: **one repository per deployable thing; branches only for
changes in flight.**

| From | To | State |
|---|---|---|
| `Claude` @ `claude/foxd-tender-backend-NiPeb` | `CRM-backend` @ `main`, private | ✅ done, Render cut over |
| `tender-tracker-pro` | `CRM-web` | ✅ done, Lovable still syncing |
| `foxd-hub-9c7dc867` | `foxd-tools` | ⬜ Phase 3 |
| `foxd-4992dbd1` | `foxd-website` | ⬜ Phase 3 |
| `merrigums` | `merrigums` — unchanged; already matches its domain, and it is a separate business | ✅ nothing to do |
| `Claude` @ `tool-inventory-app-7qfn6` | `foxd-tool-inventory` | ⬜ Phase 4 |
| `COD` @ `claude/bo7-…-wdccrm` | `COD` @ `main` | ⬜ Phase 4 |
| `Claude` @ everything else | Archived refs, then deleted | ⬜ Phase 5 |
| `Claude` (repo) | Archived, or `main` + README index | ⬜ Phase 5 |
| `CRM-Backend-snapshot-2026-04`, `FOXD` | Deleted | ⬜ Phase 5 |

The backend and frontend are named as a pair (`CRM-backend` / `CRM-web`),
which also matches the existing Render service name `crm-backend-pza6`.

## Cleanup sequence

### Phase 0 — make everything reversible — **DONE, 20 Aug 2026**

All fourteen branch tips in this repo are preserved on the remote under
`archive/2026-08-20/<branch>`, each verified to point at the exact tip
commit. Nothing here can be lost to a branch delete from now on.

These are **refs rather than tags** because the assessing session's
credentials could push only its own working branch (`git push --tags`
returned 403), so the refs were created through the GitHub API instead. Tags
are the better tool — they signal immutability and stay out of the branch
list. To convert, from a machine with normal push rights:

```sh
git fetch origin
for r in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin/archive); do
  n="${r#origin/archive/2026-08-20/}"
  git tag "archive/2026-08-20/$n" "$r"
done
git push origin --tags
# then drop the archive/* branches, now that tags hold the same commits
git for-each-ref --format='%(refname:short)' refs/remotes/origin/archive \
  | sed 's|^origin/||' | xargs -n1 git push origin --delete
```

The `COD` repo has one branch that the plan only ever adds to, so it needs no
archive ref.

### Phase 1 — de-risk the production deploy — **DONE, 20 Aug 2026**

Render config read from the dashboard and recorded with the date. `c2e92d0`
fast-forwarded onto the live branch after validating the merged state.
CI written and validated, then landed as part of Phase 2.

### Phase 2 — extract the backend — **DONE, 21 Aug 2026**

`mckjesse/CRM-backend`, private, `main` as default, **full 64-commit
history** — deliberately, because `docs/DECISIONS.md` cites around forty
SHAs and a fresh-start repo would have broken every one. Spot-checked after
the push: `dde299c`, `bd28741`, `67d9900`, `37de8c5`, `cd66dfa`, `984612e`
all resolve.

The extraction commit also did the documentation work the move required:
`CLAUDE.md`'s entire premise had been *"you are on one branch of a
fourteen-app monorepo, check which one before you commit"* — a branch map
that becomes false the instant the code stands alone. Rewritten for a
single-app repo; everything from "Stack and layout" down was already
repo-agnostic and untouched. The vestigial root `index.html` was removed
(see Phase 10 in that repo's `DECISIONS.md` for why it finally could be),
and a wrong note claiming the suite cannot run in a Claude Code container
was replaced with the recipe that works.

Render was then repointed and a deploy verified in its Events tab, and
Auto-Deploy set to `After CI Checks Pass`.

### Phase 3 — rename the frontends — **PART DONE**

- ✅ `tender-tracker-pro` → `CRM-web`. Lovable's GitHub sync survived:
  `lovable-dev[bot]` pushed three commits under the new name shortly after.
- ⬜ `foxd-hub-9c7dc867` → `foxd-tools`
- ⬜ `foxd-4992dbd1` → `foxd-website`
- `merrigums` stays as it is.

Both remaining repos are Lovable projects, and `foxd-4992dbd1` is a live
public-facing site — rename one, confirm Lovable still syncs and the site
still loads, then do the other. Add a short `CLAUDE.md` to each naming its
counterpart API.

### Phase 4 — consolidate loose tools — **MOSTLY DONE, 21 Aug 2026**

- ✅ All six single-file tools are in `mckjesse/foxd-apps`, one directory
  each, with a landing page, README and `CLAUDE.md`. The parity check the
  earlier plan called for became moot: `foxd-hub` was deleted, so the HTML
  originals are the only versions and went across directly.
- ✅ `COD` needs no migration — see above. It still wants a `main` and its
  `claude/*` branch deleted.
- ⬜ **The tool inventory is the open piece.** `7qfn6` is the right base on
  its data model, but it has **no tests and no documentation**, so extracting
  it means writing both — a bigger job than the backend was, where 160 tests
  already existed. Options: extract as one repo, split api/web to mirror the
  CRM pair, leave it until it is actually wanted, or write tests first.

### Phase 5 — retire the monorepo — **the remaining work**

`main` now exists on `Claude`, holding this file plus a README that points at
the new repos. Everything below needs a permission this session does not
have: branch deletion returns HTTP 403, and the default branch cannot be
changed via the API here.

**1. Switch `Claude`'s default branch to `main`** (Settings → General). This
must happen first — GitHub refuses to delete a default branch, and
`claude/variation-register-app-oXKwO` is currently it.

**2. Delete these thirteen branches** (Branches page → trash icon). Every one
is verified archived under `archive/2026-08-20/*` at a matching SHA:

```
claude/chat-history-github-upload-ro7k35    claude/parking-cost-tracker-8hfUy
CRM-Backend                                 claude/tender-scorecard-app-wD4lq
Tool-tracker-app                            claude/tender-tracking-crm-oX0mN
claude/ceiling-grid-calculator-poae9        claude/cod-team-randomizer-dvscjb
claude/sliding-door-calculator-BNpIe        claude/tool-inventory-app-7qfn6
claude/quote-request-tracker-9sxkl          claude/tool-inventory-app-A6PBz
claude/variation-register-app-oXKwO   ← only after step 1
```

That leaves `main`, `claude/git-repos-cleanup-7a2mga`,
`claude/foxd-tender-backend-NiPeb` (the backend rollback path) and the
fourteen `archive/*` refs — 29 branches down to 17.

**3. `COD`** — set `main` as default, then delete
`claude/bo7-game-mode-randomizer-wdccrm`.

**4. The leftovers, at your discretion**

- `CRM-Backend-snapshot-2026-04` — safe to delete, but its single commit
  `8f3b821` exists in no other repository, so deleting it is final.
- `FOXD` — empty, zero commits. Delete or use the name.
- `foxd-apps` and `foxd-tool-inventory` were created public. Neither holds
  credentials or customer data, but private is the better default for
  internal tooling.
- `claude/foxd-tender-backend-NiPeb` — retire once you have had a few clean
  deploys from `CRM-backend`.

## The agent architecture

Built after the tidy-up, and worth recording because no single repository
explains it:

```
foxd-ea (Ava)              the Executive Assistant — Claude Code project
    │                      NOT IN GIT as at 22 Aug 2026
    ▼
CRM-agent                  specialist sub-agent, 22 tools
    │                      no DB access, no Django access,
    │                      cannot self-approve consequential actions
    ▼
/api/agent/                controlled surface in CRM-backend:
    │                      API-key auth, throttling, permissions,
    │                      approval workflow, audit trail
    ▼
Django CRM ──► PostgreSQL
```

The constraint is the design: the agent reaches the CRM only through an
API built for it, so the blast radius of a mistake is whatever
`apps/agent/` permits and nothing more. Both halves carry their own tests —
`apps/agent/tests/` in the backend, `tests/` in `CRM-agent` — covering auth,
approvals, safe writes and duplicate protection.

**The weak link is `foxd-ea`.** Ava sits at the top of that chain and is the
only part of it not in version control. Everything below her is backed up and
tested; she is a folder on one disk.

Also unaccounted for: `C:\Dev\Agents\foxd-crm` is a git repository whose
remote was never confirmed. Check `.git/config` for a `[remote "origin"]`
before assuming it is backed up.

## Rules going forward

Each maps to something that went wrong above.

- **One repo per deployable thing.** If it deploys, or someone uses it on
  its own, it is a repository — never a branch.
- **Every repo has `main`, and `main` is the default.** `Claude` and `COD`
  still have none; `CRM-backend` was created this way from the first commit.
- **Deploy from `main` only** — never a `claude/*` branch. If auto-deploy is
  on, `main` must always be releasable.
- **Branches are short-lived and named for the change**: `feat/award-date`,
  `fix/csv-import`, `chore/bump-django`. Delete on merge.
- **Merge pull requests, don't close them.** All four PRs here were closed
  unmerged; that is exactly how the backend forked three ways.
- **`.gitignore` before the first commit**: `__pycache__/`, `*.pyc`, `.env`.
- **Business systems are private.** `CRM-backend` is private — though it was
  created public by accident and caught by checking, so verify rather than
  assume. Set visibility at creation, not afterwards.
- **A `CLAUDE.md` in every repo root.** The backend's version is the model —
  it exists because a design conversation was lost, and it works.

## Still open

| Item | Status |
|---|---|
| Tool inventory architecture | **Resolved and extracted** — `7qfn6` is now `mckjesse/foxd-tool-inventory` |
| `foxd-4992dbd1` | **Resolved** — the FOXD public site; rename `foxd-website` |
| `merrigums` | **Resolved** — live site, name already correct |
| The `Claude` repo's ending | **Open** — archive outright, or keep `main` + README index. This file is the obvious content for that README. |
| **`foxd-ea` is not in git** | **Open, and the most exposed thing in the estate.** Ava is the top of the agent chain and the only part of it not in version control. Publish her private; write the `.gitignore` first (`.env`, `.venv/`, `state/log/`) so connector credentials do not go up with her. |
| `Agents/foxd-crm` | **Unknown** — a git repository on disk whose remote was never confirmed. |
| When to delete the old branches | **Open** — nothing is deleted yet. `claude/foxd-tender-backend-NiPeb` @ `c2e92d0` is the rollback path if the new repo misbehaves. Retire it once you have a few clean deploys. Twelve of the fourteen branches are now fully superseded and ready to go. |
| The tool inventory | **Open** — the last piece of Phase 4. See Phase 4 below. |
| `foxd-apps` visibility | **Open** — it was created public. Low risk: no client names, no rates, no credentials, and the tools hold no data outside the visitor's own browser. The only exposure is the shape of the tender-qualification criteria. Private is still the better default for internal tooling. |

## Two non-git findings

- **Hardcoded Airbnb calendar token.** `merrigums`'s `airbnb-calendar` edge
  function has the private iCal export URL — token and all — hardcoded in
  source rather than read from a Supabase secret. That link exposes the
  property's whole booking calendar to anyone holding it, with no
  authentication. The repo is private, which contains the blast radius, but
  the token should move to an environment secret and be rotated in Airbnb.
- **Contact email mismatch.** On the FOXD site's `/book` page the form
  submits to `jesse@foxd.co` while the footer advertises
  `jesse@foxdgroup.com.au`. One is probably wrong on a live lead-capture
  page.

## Verification notes

Findings are from branch topology, merge bases, migration sets, line counts,
data models, auth and deploy configuration across all the repositories.

Credential hygiene is otherwise sound: no database passwords, no Django
`SECRET_KEY`, no Supabase `service_role` key. The committed `.env` files hold
only values that ship to the browser anyway — API base URLs and a Supabase
*publishable* anon key.

Render's deploy configuration is not a guess — it was read from the
dashboard (20 Aug for the original, 21 Aug after the cutover). It remains a
dashboard setting no file can guarantee, and it has been misrecorded in both
directions before, so re-check it rather than trusting this line.

**What was verified here, and what was taken on report.** Verified directly:
the 64-commit history and its SHAs on `CRM-backend`; the repo's private
flag (checked via an anonymous read returning 404, after an authenticated
API call reported `private: false` and caught it being public at creation);
CI run #1 green with every step passing; `CRM-web`'s Lovable sync alive
after the rename, evidenced by `lovable-dev[bot]` commits. Taken on report,
because this environment's egress policy blocks `*.onrender.com` and Render
posts nothing back to GitHub: that the post-cutover deploy succeeded, and
that Auto-Deploy is now `After CI Checks Pass`.

Both `.env` values in `CRM-web` were checked as still correct after the
cutover — repointing a Render service's source repo does not change its
hostname. DNS confirms `api.foxd.co` → `216.24.57.7` and
`crm-backend-pza6.onrender.com` → `216.24.57.15`, both Render. The two files
are not in conflict: Vite loads `.env` for dev and `.env` + `.env.production`
for `vite build`, which is what `netlify.toml` runs.

Still worth verifying: feature parity of the two calculators already ported
into `foxd-hub`, before their source branches are retired.
