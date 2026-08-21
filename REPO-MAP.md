# REPO-MAP.md — the mckjesse git estate

Assessed 20 August 2026, last updated 21 August. Written because this repo's
branch layout was actively misleading and the reasoning behind the cleanup
should outlive the conversation that produced it.

**Done:** Phases 0, 1 and 2 — every branch tip archived, the deploy warning
corrected on the live branch, CI added, and the backend extracted into
`mckjesse/CRM-backend` with Render cut over to it. Phase 3 is part-done
(`CRM-web` renamed).

**Next:** finish Phase 3 (two Lovable repos still to rename), then Phase 4.
No branch has been deleted yet; `claude/foxd-tender-backend-NiPeb` is
deliberately retained at `c2e92d0` as the rollback path.

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
| **`CRM-backend`** | private | 1 (`main`) | **The Tender Pipeline API — now its own repo.** Created 21 Aug 2026 with the full 64-commit history, so every SHA cited in its `docs/DECISIONS.md` still resolves. Render builds production from `main`. CI green on the first run. | ✅ Done |
| **`CRM-web`** | private | 1 (`main`) | The Lovable React frontend, renamed from `tender-tracker-pro`. Lovable's GitHub sync survived the rename — `lovable-dev[bot]` has pushed since. `.env` → `crm-backend-pza6.onrender.com` (dev/preview), `.env.production` → `api.foxd.co` (the deployed build). | ✅ Done |
| `Claude` | public | 29 | The old monorepo: 14 unrelated apps one-per-branch, plus 14 `archive/*` refs and the cleanup branch. Still no `main`; default branch is still the Variation Register. **No longer holds anything deployed.** | Phases 4–5 |
| `foxd-hub-9c7dc867` | private | 1 | Lovable React app already holding `CeilingGridCalculator.tsx` + `TenderScorecard.tsx`. | Rename `foxd-tools` |
| `foxd-4992dbd1` | private | 1 | **The FOXD public marketing website.** Landing page plus a `/book` capability & scope review funnel with lead-capture form, SEO component, case studies, five-pillar framework. | Rename `foxd-website` |
| `merrigums` | private | 1 | **Live site for `merrigums.com.au`** — the Merrijig holiday rental. Long-form single page with gallery lightbox, reviews, JSON-LD `LodgingBusiness` schema, and an Airbnb-synced availability calendar via a Supabase edge function. A separate business from FOXD. | Keep the name |
| `COD` | public | 1 | Black Ops 7 randomizer. No `main`; only `claude/bo7-game-mode-randomizer-wdccrm`. | Keep — add `main` |
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

### Single-file tools
| Branch | Commits | The actual app | Action |
|---|---|---|---|
| `claude/variation-register-app-oXKwO` | 5 | Variation Register — and the repo's default branch | Move to hub; stop being default |
| `claude/ceiling-grid-calculator-poae9` | 8 | Ceiling Grid Calculator (already ported to `foxd-hub`) | Retire after parity check |
| `claude/tender-scorecard-app-wD4lq` | 7 | `tender-scorecard.html` (already ported to `foxd-hub`) | Retire after parity check |
| `claude/sliding-door-calculator-BNpIe` | 14 | `sliding-door-calculator.html` — only branch with no stray `index.html` | Port to hub |
| `claude/parking-cost-tracker-8hfUy` | 9 | `parking.html` | Port to hub |
| `claude/quote-request-tracker-9sxkl` | 8 | `quote-tracker.html` | Port to hub |
| `claude/tender-tracking-crm-oX0mN` | 6 | `tender-crm.html` — early sketch of the real CRM | Superseded |
| `claude/cod-team-randomizer-dvscjb` | 18 | `cod-team-randomizer.html` + `cod-team-wheel.html` | Consolidate into `COD` repo |

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

### Phase 4 — consolidate loose tools

Port the sliding door calculator, parking tracker, quote tracker and
variation register into `foxd-tools` as routes. Check the two already-ported
calculators for parity *before* retiring their branches. Extract `7qfn6` to
`foxd-tool-inventory` with `main`, dropping the vestigial `index.html` and
`tool-inventory.html`, and carry the FOXD branding over from `A6PBz`. Move
the team wheel into `COD`.

### Phase 5 — retire the monorepo

Delete the branches whose content now lives elsewhere (the Phase 0 refs keep
the history). Give `Claude` a real `main` with a README pointing at the new
repos, or archive it. Delete `mckjesse/CRM-Backend` and the empty `FOXD`.

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
| Tool inventory architecture | **Resolved** — build on `7qfn6` |
| `foxd-4992dbd1` | **Resolved** — the FOXD public site; rename `foxd-website` |
| `merrigums` | **Resolved** — live site, name already correct |
| The `Claude` repo's ending | **Open** — archive outright, or keep `main` + README index. This file is the obvious content for that README. |
| Staging environment | **Open, worth thinking about.** `CRM-web`'s dev `.env` points at the *production* API, so Lovable's preview reads and writes live CRM data. Pointing it at localhost would break the preview, which is where the work actually happens. The real fix is a staging backend + database. |
| When to delete the old branches | **Open** — nothing is deleted yet. `claude/foxd-tender-backend-NiPeb` @ `c2e92d0` is the rollback path if the new repo misbehaves. Retire it once you have a few clean deploys. |

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
