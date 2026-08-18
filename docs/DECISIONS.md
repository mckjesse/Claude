# Decision log — FOXD Tender Pipeline backend

Reconstructed from git history (commit messages on this repo are unusually
detailed, and carry the reasoning). This is the substitute for the lost
design conversation: **what** was decided, **why**, and **which commit**
to read for the full account.

Read with `docs/ARCHITECTURE.md` (the current state) and `../CLAUDE.md`
(the rules that follow from these decisions).

> Every commit below is authored `Claude` unless noted. `git show <sha>`
> for the full message — several are near-essays and worth reading before
> changing the area they cover.

---

## Phase 0 — Feb 2026: a different app

`dde299c` → `bd28741` build the **Variation Register** app for commercial
fit-out projects (Fit Out By Design branding): a single-file
`index.html`, restyled across four commits into a dark theme.

**This has nothing to do with the tender pipeline backend.** It survives
in the tree as a root-level `index.html` that a merge carried along. It
is not served, not referenced, and not maintained. Left in place rather
than deleted because it is the only copy on this branch line and deleting
it was never asked for.

---

## Phase 1 — 11 Apr 2026: the backend, built in one day

Seven commits laid down the whole architecture. The layering established
here is still the shape of the codebase.

| Commit | Decision |
|---|---|
| `67d9900` | Scaffold: custom `AppUser` with a `role` field from the start (no bolted-on profile model), plus the six pipeline domain models |
| `b20280c` | CSRF enforced on login *(later reversed — see `37de8c5`)* |
| `99c3c45` | The DRF layer: serializers, filters, viewsets, custom actions |
| `62f7e35` | Dashboard + reporting endpoints as **thin views over a service layer** — business logic never lives in a view |
| `5291506` | **Two-layer authorisation**: permission classes for *what you may do*, `services/scoping.py` for *which rows you may see*. Split deliberately so neither concern leaks into the other |
| `b24cd57` | Automatic activity logging driven from the **DRF viewset lifecycle, not model signals** — signals cannot see the acting user without thread-locals. Accepted cost: admin and shell changes produce no activity entries |
| `604b1f5`, `9e975f7` | Admin polish, `seed_demo` with a fixed random seed, and the first test suite |

The signals-vs-viewset-hooks call in `b24cd57` is the one most likely to
be revisited by someone who doesn't know it was deliberate. It was.

---

## Phase 2 — 11–15 Apr 2026: getting deployed hurt

Eleven commits, almost all of them fighting cross-origin auth between a
Lovable-hosted React frontend and a Render-hosted Django backend. The
settings comments that look paranoid are scar tissue from these.

| Commit | Problem → fix |
|---|---|
| `1311fae` | Production packaging: Dockerfile, gunicorn, WhiteNoise, Render notes |
| `1c73026` | `python-decouple` mis-loaded env values → switched to `python-dotenv` |
| `5ce7f22`, `3aa1f8e` | Frontend couldn't bootstrap CSRF → `GET /api/users/csrf/`, returning the token **in the JSON body** because a cross-origin frontend cannot always read the cookie |
| `83be7b7` | Render assigns a hostname per service → auto-wire `RENDER_EXTERNAL_HOSTNAME` into `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` instead of hand-listing it |
| `cd5acbe` | An unparseable `DATABASE_URL` took the service down → fall back to discrete `DB_*` vars |
| `3ec05e2`, `eaa975b` | Cross-site cookies rejected → `SameSite=None` + `Secure=True`, set **unconditionally** rather than gated on `DEBUG`, so a mis-set `DEBUG` at deploy time can't silently break auth |
| `dcb7a95` | A stale `Domain` env var made browsers drop the cookie → pin both cookie `Domain`s to `None` |
| `fc39b47` | Trailing slashes in env origins silently broke Django's exact-match comparison → `_csv()` strips them |
| `cbe78e4` | `CorsMiddleware` duplicated by a merge → deduplicated, kept first in the list |

**Do not "clean up" the settings comments in this area.** Each one
records a specific outage.

---

## Phase 3 — 14–15 Apr 2026: shaping the API for the frontend

The frontend needed fewer round-trips and one predictable convention.

- `4a2faa5` — **The `_detail` convention.** Writable relations stay plain
  FK ids (the frontend uses them for routing and cache keys); the nested
  read-only object sits beside them as `<field>_detail`. This is the
  single most load-bearing serializer convention in the codebase.
- `efffe99` — `OpportunitySummarySerializer` as the canonical nested
  opportunity, introducing **`project_id` as a read-only alias for
  `project_code`** (the DB column can't be named `id`).
- `474af77`, `3fde1bb` — Widened nested shapes so list rows render
  without extra requests: `company_name` on a follow-up's opportunity;
  `primary_email` / `primary_phone` on an opportunity's company.
- `4bc5086` — `loss_reason` (category key, for grouping) and
  `loss_reason_detail` (full summary with label) exposed inline on the
  opportunity, so loss reporting needs no second request.
- `968b26a` — Widened `OPPORTUNITY_TRACKED_FIELDS`. Activity tracking is
  a **curated list**, not every field; adding a model field does not make
  it logged.
- `fdba986` — `project_code` promoted to required and unique, and
  established as the human-facing "Project ID" throughout the UI.
  *(Superseded eight days later — see `1437f99`.)*

---

## Phase 4 — 15 Apr 2026: quote automation and the state model

Two hard problems solved together, and the source of most of the current
invariants.

### Automatic quotes

`1ecae33` introduced the rule: an opportunity in an eligible stage with a
positive value always has at least one Quote. `b759c35` extended it to
`mark_won` and `mark_lost`.

`6a80c60` then made the Opportunity→Quote **field mapping explicit** in a
single `_build_quote_payload()` function — "no serializer magic, no
signals, no implicit defaults hidden in the model" — with an ASCII
mapping table in the docstring. `4bcf727` and `709e825` added
`prove_quote_creation`, a management command that *asserts* the mapping
end to end, and `ba0ef12` added greppable INFO logging on every decision
branch plus `backfill_quotes` for historical rows.

The theme: this automation is invisible to users, so it was made
**provable and greppable in production** rather than merely tested.

### The won/lost state model

`e3eb6f4` is the key commit. `mark_won`/`mark_lost` already behaved
correctly, but a direct `PATCH` could produce inconsistent states. The
fix moved enforcement into `OpportunitySerializer.validate`, so **every**
write path — POST, PATCH and the actions — lands consistently:

- `stage` = pipeline progression and outcome; `status` = lifecycle
  (open/closed). **Two axes, not one.**
- `stage=won` ⇒ `final_awarded_value` required, `status` forced to
  `closed`.
- `stage=lost` ⇒ a `LossReason` must already exist, else 400 pointing at
  `mark_lost` — which creates it atomically. There is no "lost without a
  reason" state.

The payoff, stated in the commit: dashboard metrics can now rely on
`won = stage=won ∧ status=closed` and
`lost = stage=lost ∧ status=closed ∧ loss_reason`.

---

## Phase 5 — 16–20 Apr 2026: controlled reversal and soft delete

- `9f417bf` — `GET /api/loss-reason-choices/` so the Lost modal's
  dropdown comes from the backend, not a hardcoded frontend list.
- `80c2ddd` — `POST /api/opportunities/{id}/reopen/`. Because guard 1
  blocks PATCHing out of a terminal stage, reversal needed an explicit
  door. It moves the opportunity to `follow_up`/`open` and **preserves
  the historical LossReason and all quotes** — reopening is not an
  undo of history.
- `a70cc1c` — **Soft delete.** `archived_at`/`archived_by`, plus
  `archive`/`restore` actions, and hard `DELETE` **rejected with 400
  unless the row is already archived**. The reasoning: forcing archive
  first guarantees the archive event is in the activity feed even if the
  row is later destroyed. `scoped_opportunities` excludes archived rows
  by default, which is how dashboard and reports stopped counting them
  *without any change to their own code*.
- `3c71c25` — Cascaded archive filtering to child records via the parent
  opportunity — **except `scoped_activity`**, which never filters on
  archive state, because otherwise the "archived" event itself would
  disappear from the audit trail.

---

## Phase 6 — 22–24 Apr 2026: multi-builder pricing, and JWT

### `1437f99` — uniqueness scoped to the company

The single most business-specific decision in the repo. FOXD prices the
same project to **multiple builders**, so the global unique constraint
from `fdba986` was returning 400 on legitimate data.

```
Old:      project_code globally unique
New:      unique per (project_code, company)
Allowed:  FOXD-2026-001 + Acme Builders  AND  FOXD-2026-001 + Kingsway Build
Blocked:  FOXD-2026-001 + Acme Builders  AND  FOXD-2026-001 + Acme Builders
```

Migration `0006` drops the old index and adds the compound constraint;
DRF auto-derives a `UniqueTogetherValidator` so duplicates surface as
400, not 500. This decision is what makes Phase 7's
`close_related_as_lost` necessary.

### `37de8c5` — SimpleJWT replaces session auth

**Session/CSRF auth was unreliable on iPad Safari** because of cross-site
cookie restrictions — which is what all of Phase 2 had been fighting. JWT
became the primary frontend auth path (30-minute access, 7-day refresh,
rotation on); `SessionAuthentication` was kept only for the Django admin
and the DRF browsable API. `LoginView` dropped `@csrf_protect` and the
session login call and set `authentication_classes = []`.

**The README was never updated** and still documents session + CSRF auth
and claims "no JWT". That drift is live today.

Also in this phase: `111d752` added `GET /api/users/` so the frontend can
populate estimator/assignee dropdowns.

---

## Phase 7 — 27–30 Apr 2026: follow-up workflow and grouped outcomes

- `a73045f` — Auto-create a follow-up when an opportunity enters
  `submitted`, due 14 days after the submission date. Fires **only on the
  transition in**, with a duplicate guard on the canonical subject, so it
  is idempotent.
- `e993bc8` → `978add4` — The completion workflow, then an important
  reversal: completing a task originally **always** created a successor.
  `978add4` made that opt-in via `schedule_next` (default **false**), so
  the caller must choose between closing out for good and scheduling
  another. Notes became required; the duplicate guard stayed.
- `494a873` — **`close_related_as_lost`.** The direct consequence of
  `1437f99`: winning one opportunity leaves its sibling opportunities
  (same `project_code`, different builders) dangling open. This action
  closes each as lost with category `project_won_other` and the winning
  builder as `competitor_name`. Deliberately **user-triggered, not
  automatic** — "the frontend invokes this explicitly so the user retains
  control." Never touches the won opportunity itself; no-ops cleanly when
  nothing is open.
- `32ff917` — `is_archived` field + `?include_archived=true` as an alias
  for `?archived=all`.
- `2854f0e` — `schedule_next` arrived from the frontend as a **string**,
  not a bool. Fixed with tolerant parsing (bools, `"true"`/`"1"`/`"yes"`,
  ints) and INFO logging on the whole path.

---

## Phase 8 — 6 May – 15 Jul 2026: frontend-driven corrections

Each of these started as a frontend/backend contract mismatch.

- `404d2fa` — DRF's `PageNumberPagination` silently ignores
  `?page_size=`, so a frontend asking for 500 follow-ups got 25 and the
  list looked incomplete. Fixed with `StandardPagination`
  (`page_size_query_param`, max 500).
- `d248760` — Frontend sent `opportunity_id`; the filter only accepted
  `opportunity`. Added the alias so **either key works**.
- `84670d8` — Free-text activity notes failed because `entity_type` and
  `activity_type` had no defaults. Now defaulted (`"opportunity"`,
  `"note"`), `entity_id` auto-filled from the opportunity and
  `created_by_user` stamped server-side, so a note is
  `{"opportunity": id, "description": "..."}` and nothing more.
- `7e07ed5` → `63a4de1` — **Built then removed in the same phase.** An
  `apps/accounts` package introduced `Builder` and `Contact` models that
  duplicated the existing `Company` and `Contact`. `63a4de1` deleted all
  13 files and instead added six account-management fields to `Company`
  (`account_tier`, `margin_quality`, `account_owner`,
  `relationship_notes`, `last_contact_date`, `next_contact_date`), with
  migration `0009` dropping the orphaned `accounts_*` tables via
  `RunSQL`. **`Company` is the single source of truth** for both pipeline
  reference data and account management. Don't reintroduce a parallel
  builder model.
- `fd3115b` — The frontend posted `reason_category="no_response"`; the
  backend only accepted `"no_decision"`. The whole category set was
  standardised: `client_change`→`cancelled`,
  `no_decision`→`no_response`, `program` added, `timing` and `capability`
  folded into `other`, labels updated. Migration `0010` **remaps existing
  rows before narrowing the choices**. A second route
  `GET /api/loss-reasons/options/` was added because `options` under the
  `loss-reasons` router was being captured as a pk — which is why
  `extra_patterns` must precede `router.urls` in `apps/pipeline/urls.py`.
- `cd66dfa` — **The stale rule was wrong.** It used a 14-day threshold
  against `activity_logs` ordered by `updated_at`, surfacing
  opportunities far too early. Replaced with the intended business rule:
  30 days since the *effective submission date*, restricted to
  `{submitted, follow_up, negotiating}`, and excluded when a
  pending/in-progress follow-up is due today or later. The effective date
  resolves through a four-step priority chain where `updated_at` is a
  **fallback only, never primary** — and the resolver returns an
  `is_true_submission` flag so callers know when they're on the fallback.

---

## Reversals worth knowing about

Four decisions in this history were **replaced**, not extended. If you
find yourself proposing one of these, you are proposing a revert:

| Original | Replaced by | Why |
|---|---|---|
| `project_code` globally unique (`fdba986`) | Unique per company (`1437f99`) | FOXD prices one project to several builders |
| Session + CSRF auth (`b20280c`, `5ce7f22`) | SimpleJWT (`37de8c5`) | Cross-site cookies unreliable on iPad Safari |
| Completion always creates a successor (`e993bc8`) | Opt-in `schedule_next` (`978add4`) | The user must be able to close out for good |
| Separate `accounts` app (`7e07ed5`) | Fields on `Company` (`63a4de1`) | Duplicated existing models |

Plus one rule corrected outright: the stale threshold moved from
"14 days of no activity" to "30 days since submission" (`cd66dfa`).

---

## Phase 9 — 30 Jul 2026: production domains, Mark Won, terminal hygiene

Three commits that live **only** on `claude/foxd-tender-backend-NiPeb`,
the branch Render deploys. They were never merged into `CRM-Backend`,
which is why that branch is a stale mirror rather than the integration
target its name and history suggest.

- `984612e` — **Mark Won workflow.** Adds `award_date` (migration `0011`)
  as the date an opportunity was actually won, distinct from the
  forward-looking `expected_award_date`. `mark_won` gains real guards: a
  lost opportunity is rejected with a 400 telling you to reopen, and an
  archived one with a 400 telling you to restore — resolved through
  `_get_opportunity_for_archive_path` specifically so the archived case
  returns a clear 400 instead of a bare 404.
- `e6a5ef1` — **Production domains baked in.** `api.foxd.co` and
  `crm.foxd.co` are merged into `ALLOWED_HOSTS` and the CORS/CSRF origins
  as a baseline on top of the env vars, so the service cannot be knocked
  offline by a drifting environment variable. The commit message notes
  that JWT auth is what makes the cross-domain split viable at all: no
  session or csrftoken cookie is involved, so the browser's cross-site
  cookie policy is irrelevant. The Render URL and Lovable origin are kept
  deliberately during the cutover.
- `11097a5` — **Terminal follow-up hygiene.** When an opportunity goes
  terminal, outstanding follow-ups are **cancelled, not deleted**, with a
  note, timestamp and acting user, so history survives; and the dashboard
  independently excludes follow-ups whose parent opportunity is terminal.
  Belt and braces on the same rule. This also changed the response shape
  of `mark_won` / `mark_lost` to wrap the opportunity alongside
  `cleared_followups_count` and `cleared_followup_ids`.

## Phase 10 — 18 Aug 2026: review and debug pass

A read of the whole app turned up five bugs, each reproduced against a
live Postgres test database before being fixed:

1. `_top_overdue_followups` ordered by `-priority` on a CharField, so it
   sorted alphabetically and returned medium, low, high, critical — the
   dashboard panel for urgent work put `critical` last. Replaced with an
   explicit `_PRIORITY_RANK` Case/When.
2. `mark_won` / `mark_lost` serialised from a stale prefetch cache,
   reporting `latest_quote: null` for a quote they had just created and
   advertising a `next_followup` the terminal sweep had already
   cancelled. Added `_fresh_data()`.
3. `close_related_as_lost` swept up **archived** opportunities, mutating
   soft-deleted rows.
4. The same action logged a hardcoded `Stage.FOLLOW_UP` as the previous
   stage, so an opportunity closed from `pricing` produced a false audit
   entry.
5. `mark_lost` had no won-guard, so a won opportunity could be flipped to
   lost while keeping its `final_awarded_value`. (`mark_won` already had
   the mirror guard from `984612e` — that one was left alone as the better
   implementation.)

## Reading the history

Branch topology: work was done on `claude/foxd-tender-backend-NiPeb` and
merged into `CRM-Backend` at `e205927` (15 Apr), `2346f40` (30 Apr) and
`8465436` (15 Jul). That produced **duplicated commits** — "Fix page_size
query param", "Fix activity note creation", "Strip trailing slashes",
"Enable cross-site cookies", "Harden DATABASES", "Auto-wire Render's
injected hostname" and "Add opportunity_id filter alias" each appear
twice with different SHAs. They are merge artefacts, not two separate
fixes.

`7d1d2c0` ("Add files via upload") and `3f182a2` are the only commits by
`mckjesse` rather than `Claude`.

Several commit messages carry a `https://claude.ai/code/session_…` link
to the originating session. Those sessions are the history that was lost;
the links are unlikely to resolve to anything usable, which is why this
file exists.
