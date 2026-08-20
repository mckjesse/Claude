# REPO-MAP.md — the mckjesse git estate

Assessed 20 August 2026. Written because this repo's branch layout is
actively misleading and the reasoning behind the cleanup should outlive the
conversation that produced it. **No repository was changed by that
assessment** — this file is a map, not a record of work done.

## The one-line summary

`mckjesse/Claude` uses **branches as if they were repositories**: fourteen
branches, each an unrelated application, all descending from one root
commit. Everything else that is wrong follows from that.

## Estate at a glance

| Repo | Vis. | Branches | What it is | Disposition |
|---|---|---|---|---|
| `Claude` | public | 14 | Fourteen unrelated apps, one per branch. No `main`. Default branch is the Variation Register. Holds the production backend. | Split, then archive |
| `tender-tracker-pro` | private | 1 | Lovable React frontend for the Tender Pipeline; `.env` → `crm-backend-pza6.onrender.com`. The other half of the live system. | Live — rename `foxd-tender-web` |
| `foxd-hub-9c7dc867` | private | 1 | Lovable React app already holding `CeilingGridCalculator.tsx` + `TenderScorecard.tsx`. | Adopt as `foxd-tools` |
| `foxd-4992dbd1` | private | 1 | Lovable React; `Book.tsx`, `ProjectsPage.tsx`. Purpose unclear from code. | Confirm |
| `merrigums` | private | 1 | Lovable + Supabase scaffold; only `Index.tsx` / `NotFound.tsx`. | Confirm or archive |
| `COD` | public | 1 | Black Ops 7 randomizer. No `main`; only `claude/bo7-game-mode-randomizer-wdccrm`. | Keep — add `main` |
| `CRM-Backend` | public | 1 | Single-commit orphan snapshot of the Django backend. Unrelated history, 3 migrations vs production's 11. | Delete |
| `FOXD` | public | 0 | Completely empty. The best name in the estate, attached to nothing. | Repurpose or delete |

## Fix before anything else

1. **Production deploys from a feature branch.** Render auto-deploys the
   Tender Pipeline API from `claude/foxd-tender-backend-NiPeb` inside this
   fourteen-app repo. `entrypoint.sh` runs `migrate --noinput`, so a push
   carrying a migration rewrites the production schema. A fresh clone lands
   on `claude/variation-register-app-oXKwO` — a different app entirely.
   Confirm the current setting in the Render dashboard rather than trusting
   any file, including this one.
2. **One commit of production truth is stranded.**
   `claude/chat-history-github-upload-ro7k35` is the live branch **plus
   exactly one commit** — `c2e92d0`, which corrects `CLAUDE.md` to say that
   pushing auto-deploys to production. Merge it before deleting anything.
3. **The convincingly-named branch is the stale one.** `CRM-Backend` looks
   like the integration branch and has three "Merge branch
   'claude/foxd-tender-backend-NiPeb' into CRM-Backend" commits. That
   stopped 15 July 2026. It is now strictly behind: missing migration
   `0011_opportunity_award_date`, the Mark Won workflow, the
   production-domain config, the terminal follow-up work and two test
   modules — plus 33 committed `.pyc` files. Its schema does not match
   production.

## The backend forked three ways

```
mckjesse/CRM-Backend (repo) ── 1 commit, unrelated history, 3 migrations   → DELETE

                          ┌── CRM-Backend branch — 10 migrations, no docs/ → RETIRE
dde299c ──── cd66dfa ─────┤   (strictly behind; 33 .pyc committed)
 root       15 Jul fork   └── claude/foxd-tender-backend-NiPeb            → LIVE
                              11 migrations, CLAUDE.md + docs/, Render
                                    └── + c2e92d0 stranded on chat-history
```

The standalone `CRM-Backend` **repository** shares no git history with the
branch of the same name.

## Branches in this repo

### Backend family
| Branch | Commits | Status | Action |
|---|---|---|---|
| `claude/foxd-tender-backend-NiPeb` | 62 | Production. 11 migrations, `CLAUDE.md` + `docs/`. | Extract to own repo |
| `claude/chat-history-github-upload-ro7k35` | 63 | Live + 1 commit (`c2e92d0`). Nothing else differs. | Merge that commit, delete |
| `CRM-Backend` | 73 | Strictly behind production. Misleading name. | Retire |

### Tool inventory — three attempts at one app
| Branch | Commits | Status | Action |
|---|---|---|---|
| `claude/tool-inventory-app-A6PBz` | 25 | Furthest along: Netlify Functions + Blobs, CSV import. Contains all of `Tool-tracker-app`. | Likely the survivor |
| `Tool-tracker-app` | 14 | **Zero unique commits** — strict subset of `A6PBz`. | Delete |
| `claude/tool-inventory-app-7qfn6` | 9 | Different architecture: React + Django + Entra ID. Forked off root, never reconciled. | Pick one architecture |

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

| Today | Becomes |
|---|---|
| `Claude` @ `claude/foxd-tender-backend-NiPeb` | `foxd-tender-api` — new repo, `main`, **private** (requires repointing Render) |
| `tender-tracker-pro` | `foxd-tender-web` |
| `foxd-hub-9c7dc867` | `foxd-tools` |
| `Claude` @ `tool-inventory-app-A6PBz` | `foxd-tool-inventory` |
| `COD` @ `claude/bo7-…-wdccrm` | `COD` @ `main` |
| `Claude` @ everything else | Tagged, then deleted |
| `Claude` (repo) | Archived, or `main` + README index |
| `CRM-Backend`, `FOXD` | Deleted |

## Cleanup sequence

**Phase 0 — make everything reversible (zero risk, do first).** Tag every
branch tip before a single delete. Tags survive branch deletion, so after
this nothing can be lost.

```sh
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin); do
  git tag "archive/2026-08-20/${b#origin/}" "$b"
done
git push origin --tags
```

**Phase 1 — de-risk the production deploy.** Confirm in Render which repo
and branch it builds and whether auto-deploy is on. Merge `c2e92d0` into the
live branch (full test suite first — the push *is* a release). Then decide
the deploy gate; do not leave auto-deploy on against a branch also used for
work in progress.

**Phase 2 — extract the backend.** Create `foxd-tender-api` private, push
the live history as `main`, drop the vestigial `index.html`. Repoint Render
and **verify a real deploy including `migrate`** before touching the old
branch. Keep the old branch until one clean deploy is observed.

**Phase 3 — rename the frontends.** `tender-tracker-pro` → `foxd-tender-web`,
`foxd-hub-9c7dc867` → `foxd-tools`. GitHub redirects old URLs, but **Lovable's
GitHub connection may need reconnecting** — rename one, confirm sync, then
the other. Add a short `CLAUDE.md` to each naming its counterpart API.

**Phase 4 — consolidate loose tools.** Port sliding door, parking, quote
tracker and variation register into `foxd-tools` as routes. Check the two
already-ported calculators for parity *before* retiring their branches.
Extract `A6PBz` to `foxd-tool-inventory`. Move the team wheel into `COD`.

**Phase 5 — retire the monorepo.** Delete the branches whose content now
lives elsewhere (Phase 0 tags keep the history). Give `Claude` a real `main`
with a README pointing at the new repos, or archive it. Delete
`mckjesse/CRM-Backend` and the empty `FOXD`.

## Rules going forward

Each maps to something that went wrong above.

- **One repo per deployable thing.** If it deploys, or someone uses it on
  its own, it is a repository — never a branch.
- **Every repo has `main`, and `main` is the default.** Two repos have no
  `main` at all.
- **Deploy from `main` only** — never a `claude/*` branch. If auto-deploy is
  on, `main` must always be releasable.
- **Branches are short-lived and named for the change**: `feat/award-date`,
  `fix/csv-import`, `chore/bump-django`. Delete on merge.
- **Merge pull requests, don't close them.** All four PRs here were closed
  unmerged; that is exactly how the backend forked three ways.
- **`.gitignore` before the first commit**: `__pycache__/`, `*.pyc`, `.env`.
- **Business systems are private.** The Tender Pipeline backend currently
  sits in two *public* repos.
- **A `CLAUDE.md` in every repo root.** The backend's version is the model —
  it exists because a design conversation was lost, and it works.

## Open decisions

| Decision | Options | Unblocks |
|---|---|---|
| Tool inventory architecture | `A6PBz` (Netlify static, further along) vs `7qfn6` (React + Django + Entra ID, better auth) | Phase 4 |
| `foxd-4992dbd1` | Live project worth a real name, or archive | Phase 3 |
| `merrigums` | Empty scaffold — archive, or is there a plan? | Phase 3 |
| The `Claude` repo's ending | Archive outright, or `main` + README index | Phase 5 |

## Verification notes

Findings are from branch topology, merge bases, migration sets, committed
artefacts and deploy configuration across all eight repositories. Two things
worth re-checking rather than trusting: Render's auto-deploy setting (a
service setting no file can guarantee, and it has been misremembered in both
directions), and feature parity of the two calculators already ported into
`foxd-hub`. No secrets were found committed anywhere — the one `.env` in git
holds a public API base URL.
