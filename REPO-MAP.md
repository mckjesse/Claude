# REPO-MAP.md — the mckjesse git estate

Assessed 20 August 2026. Written because this repo's branch layout is
actively misleading and the reasoning behind the cleanup should outlive the
conversation that produced it.

**Changes made so far:** the `archive/2026-08-20/*` refs described under
Phase 0, and this file. No branch was modified or deleted, no repository was
renamed, nothing was deployed.

**Outstanding, ready to go:** the `c2e92d0` fast-forward described in item 1
below. It is validated (160 tests green, no migrations) but unpushed — the
assessing session was not permitted to write to a branch other than its own.

## The one-line summary

`mckjesse/Claude` uses **branches as if they were repositories**: fourteen
branches, each an unrelated application, all descending from one root
commit. Everything else that is wrong follows from that.

## Estate at a glance

| Repo | Vis. | Branches | What it is | Disposition |
|---|---|---|---|---|
| `Claude` | public | 14 | Fourteen unrelated apps, one per branch. No `main`. Default branch is the Variation Register. Holds the production backend. | Split, then archive |
| `tender-tracker-pro` | private | 1 | Lovable React frontend for the Tender Pipeline; `.env` → `crm-backend-pza6.onrender.com`, `.env.production` → `api.foxd.co`. The other half of the live system. | Live — rename `foxd-tender-web` |
| `foxd-4992dbd1` | private | 1 | **The FOXD public marketing website.** Landing page plus a `/book` capability & scope review funnel with lead-capture form, SEO component, case studies, five-pillar framework. | Live — rename `foxd-website` |
| `merrigums` | private | 1 | **Live site for `merrigums.com.au`** — the Merrijig holiday rental. Long-form single page with gallery lightbox, reviews, JSON-LD `LodgingBusiness` schema, and an Airbnb-synced availability calendar via a Supabase edge function. A separate business from FOXD. | Live — keep the name |
| `foxd-hub-9c7dc867` | private | 1 | Lovable React app already holding `CeilingGridCalculator.tsx` + `TenderScorecard.tsx`. | Adopt as `foxd-tools` |
| `COD` | public | 1 | Black Ops 7 randomizer. No `main`; only `claude/bo7-game-mode-randomizer-wdccrm`. | Keep — add `main` |
| `CRM-Backend` | public | 1 | Single-commit orphan snapshot of the Django backend. Unrelated history, 3 migrations vs production's 11. | Delete |
| `FOXD` | public | 0 | Completely empty. The best name in the estate, attached to nothing. | Repurpose or delete |

## Fix before anything else

1. **Production deploys from a feature branch — VERIFIED 20 Aug 2026.**
   Checked in the Render dashboard: **Source** `mckjesse/Claude`, **Branch**
   `claude/foxd-tender-backend-NiPeb`, **Auto-Deploy** `On Commit`. So a push
   to that branch *is* a production release, with no approval step.
   `entrypoint.sh` runs `migrate --noinput` on every deploy, so a push
   carrying a migration rewrites the production schema. Meanwhile a fresh
   clone lands on `claude/variation-register-app-oXKwO` — a different app
   entirely.

   This settles a contradiction in the history. The live branch's own
   `CLAUDE.md` still claims *"Pushing here does NOT deploy... set to manual
   deploy"*; commit `c2e92d0` corrects it to auto-deploy and is the accurate
   one. Until `c2e92d0` is merged, the canonical orientation doc tells a
   reader that pushes are safe when they are in fact releases. **Merging it
   is the single highest-value change in this whole cleanup.**
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

| Today | Becomes |
|---|---|
| `Claude` @ `claude/foxd-tender-backend-NiPeb` | `foxd-tender-api` — new repo, `main`, **private** (requires repointing Render) |
| `tender-tracker-pro` | `foxd-tender-web` |
| `foxd-hub-9c7dc867` | `foxd-tools` |
| `foxd-4992dbd1` | `foxd-website` |
| `merrigums` | `merrigums` — unchanged; already matches its domain, and it is a separate business |
| `Claude` @ `tool-inventory-app-7qfn6` | `foxd-tool-inventory` |
| `COD` @ `claude/bo7-…-wdccrm` | `COD` @ `main` |
| `Claude` @ everything else | Archived refs, then deleted |
| `Claude` (repo) | Archived, or `main` + README index |
| `CRM-Backend`, `FOXD` | Deleted |

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

### Phase 1 — de-risk the production deploy

Confirm in Render which repo and branch it builds and whether auto-deploy is
on. Merge `c2e92d0` into the live branch (full test suite first — the push
*is* a release). Then decide the deploy gate; do not leave auto-deploy on
against a branch also used for work in progress.

### Phase 2 — extract the backend

Create `foxd-tender-api` private, push the live history as `main`, drop the
vestigial `index.html`. Repoint Render and **verify a real deploy including
`migrate`** before touching the old branch. Keep the old branch until one
clean deploy is observed. Note the domain move is already half-built: the
frontend's `.env.production` points at `api.foxd.co` while its dev `.env`
still points at the raw `onrender.com` host, and the backend has a "prepare
for api.foxd.co / crm.foxd.co" commit — finish or abandon that deliberately
rather than leaving it half-applied.

### Phase 3 — rename the frontends

`tender-tracker-pro` → `foxd-tender-web`, `foxd-hub-9c7dc867` →
`foxd-tools`, `foxd-4992dbd1` → `foxd-website`. Leave `merrigums` alone.
GitHub redirects old URLs, but **Lovable's GitHub connection may need
reconnecting** after a rename and all three are Lovable projects — rename
one, confirm sync, then the next. Two are live public-facing sites, so load
each one after its rename rather than doing all three then checking. Add a
short `CLAUDE.md` to each naming its counterpart API.

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

## Still open

| Item | Status |
|---|---|
| Tool inventory architecture | **Resolved** — build on `7qfn6` |
| `foxd-4992dbd1` | **Resolved** — the FOXD public site; rename `foxd-website` |
| `merrigums` | **Resolved** — live site, name already correct |
| The `Claude` repo's ending | **Open** — archive outright, or keep `main` + README index |

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
data models, auth and deploy configuration across all eight repositories.

Credential hygiene is otherwise sound: no database passwords, no Django
`SECRET_KEY`, no Supabase `service_role` key. The committed `.env` files hold
only values that ship to the browser anyway — API base URLs and a Supabase
*publishable* anon key.

Render's deploy configuration is no longer a guess: Source, Branch and
Auto-Deploy were read directly from the dashboard on 20 Aug 2026 and are
recorded above. Re-check it if it matters later — it is a dashboard setting
no file can guarantee, and it has been misrecorded in both directions before.

Still worth verifying: feature parity of the two calculators already ported
into `foxd-hub`, before their source branches are retired.

The merged state of `c2e92d0` was validated here — full suite run against
PostgreSQL 16: **160 tests, all pass**; `makemigrations --check --dry-run`
reports no changes. The fast-forward push itself was blocked by this
session's permissions, so it remains outstanding.
