# mckjesse/Claude — retired

**Nothing is developed here any more.** This repository used to hold fourteen
unrelated applications, one per branch, with no `main` and a default branch
pointing at whichever app happened to be first. It was split up in August
2026.

It is kept for one reason: **history**. Every original branch tip is
preserved as `archive/2026-08-20/<branch>`, so nothing that ever existed
here has been lost.

## Where everything went

| What it was | Where it lives now |
|---|---|
| `claude/foxd-tender-backend-NiPeb` — the Tender Pipeline API | **`mckjesse/CRM-backend`** @ `main` (private) |
| `tender-tracker-pro` — its React frontend | **`mckjesse/CRM-web`** |
| Ceiling Grid Calculator | **`mckjesse/foxd-apps`** → `ceiling-grid/` |
| Sliding Door Calculator | `mckjesse/foxd-apps` → `sliding-door/` |
| Variation Register | `mckjesse/foxd-apps` → `variation-register/` |
| Quote Request Tracker | `mckjesse/foxd-apps` → `quote-tracker/` |
| Parking Cost Tracker | `mckjesse/foxd-apps` → `parking/` |
| Tender Scorecard | `mckjesse/foxd-apps` → `tender-scorecard/` |
| `claude/cod-team-randomizer-dvscjb` | **`mckjesse/COD`** — which already superseded it |
| `claude/tender-tracking-crm-oX0mN` | Superseded by `CRM-backend` + `CRM-web` |
| `CRM-Backend` branch | Superseded; was strictly behind production |

Still here, deliberately:

- `claude/tool-inventory-app-7qfn6` and `claude/tool-inventory-app-A6PBz` —
  two attempts at a tool inventory app, not yet extracted. `7qfn6` is the
  one to build on; see `REPO-MAP.md`.
- `claude/foxd-tender-backend-NiPeb` — retained as the rollback path for the
  backend extraction, at the exact commit `CRM-backend` was created from.

## The two documents here

**[`WORKING-LOCALLY.md`](WORKING-LOCALLY.md)** — start here if you want to
*do* something. The `~/Developer` layout, how to clone all eight repos
(including the four private ones), the branch-per-change workflow, and the
three hazards worth knowing before you push anything: merging to
`CRM-backend` `main` deploys to production, three repos are also written to
by Lovable's bot, and `.env` files are deliberately not in git.

**[`REPO-MAP.md`](REPO-MAP.md)** — read this to understand *why*. What every
repository and branch was, what was wrong with the layout, what was done
about it, and what is still open. It exists because the reasoning behind a
cleanup is worth more than the cleanup itself, and because the original
design conversations for this code were lost.
