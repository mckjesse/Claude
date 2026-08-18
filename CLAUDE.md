# CLAUDE.md — FOXD Tender Pipeline (backend)

Orientation for any Claude Code session working in this repo. Read this
first; it exists because the original design conversation was lost and
this file (plus `docs/`) is the replacement for it.

## What this repo actually is

`mckjesse/claude` is a **multi-project repo** — one branch per unrelated
app. This branch line is the **FOXD Tender Pipeline backend**: a Django
5 + DRF + PostgreSQL API that is the system of record for FOXD's
commercial fit-out tendering pipeline. The React frontend is a separate
codebase (hosted on Lovable); the backend is deployed on Render.

**Branch map — check where you are before doing anything:**

| Branch | Contents |
|---|---|
| `CRM-Backend` | **The integration branch for this backend. Base new work here.** |
| `claude/foxd-tender-backend-NiPeb` | Historical feature branch; merged into `CRM-Backend` repeatedly |
| `claude/variation-register-app-oXKwO` | GitHub's *default* branch — a completely different app |
| `Tool-tracker-app`, `claude/ceiling-grid-calculator-*`, `claude/tender-scorecard-app-*`, etc. | Other unrelated one-off apps |

Because the GitHub default branch is `claude/variation-register-app-oXKwO`,
a fresh clone lands on the wrong app. Always `git checkout CRM-Backend`.

`index.html` in the repo root is **vestigial** — it is the standalone
"Variation Register" app (Fit Out By Design) from Feb 2026, carried along
by a merge. Django never serves it and nothing references it. Do not
treat it as this project's frontend.

## Stack and layout

Python 3.12 · Django 5.x · DRF · PostgreSQL · django-filter ·
django-cors-headers · SimpleJWT · WhiteNoise · gunicorn · Docker/Render.

```
config/                 Django project
  settings.py           single-file, env-driven via python-dotenv
  renderers.py          FoxdJSONRenderer — forces Decimal -> str
  pagination.py         StandardPagination — honours ?page_size (max 500)
apps/users/             AppUser (custom user + role), auth endpoints
apps/pipeline/
  models.py             the 6 domain models
  serializers.py        full + "minimal"/"summary" nested serializers
  views.py              viewsets, custom actions, dashboard/report views
  permissions.py        role -> action rules (the ONLY authorisation source)
  filters.py            django-filter FilterSets
  services/
    scoping.py          role -> visible rows (row-level filtering)
    activity.py         ActivityLog writer + tracked-field sets
    quote_automation.py auto-create Quote revisions
    followup_automation.py auto-create the post-submission follow-up
    dashboard.py        /api/dashboard/ aggregation
    reports.py          the 7 report endpoints
  management/commands/  seed_demo, backfill_quotes, prove_quote_creation
docs/ARCHITECTURE.md    model graph, API surface, permission + scoping matrices
docs/DECISIONS.md       why the code looks like this, reconstructed from git
```

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set SECRET_KEY, DB_*, CORS/CSRF origins
python manage.py migrate
python manage.py seed_demo      # idempotent; --reset to wipe first
python manage.py runserver

python manage.py test           # 134 tests across 11 files
python manage.py test apps.pipeline
```

The test DB role needs `CREATEDB`: `ALTER ROLE foxd CREATEDB;`

**Note:** a bare Claude Code container has neither Django nor PostgreSQL
installed, so `manage.py test` cannot run until you `pip install -r
requirements.txt` and provide a database. Don't claim tests pass without
actually running them.

## Non-negotiable invariants

These are enforced in code and covered by tests. Breaking one is a
regression, not a refactor.

1. **`stage=won` requires `final_awarded_value`**, and forces
   `status=closed`.
2. **`stage=lost` requires a `LossReason`**, and forces `status=closed`.
   The only sanctioned path in is `POST /api/opportunities/{id}/mark_lost/`,
   which writes both atomically. A direct `PATCH` to `stage=lost` is
   rejected with 400.
3. **You cannot `PATCH` out of `won`/`lost`.** The only way back is
   `POST /api/opportunities/{id}/reopen/`, which moves the opportunity to
   `follow_up` / `open` and **preserves** the historical `LossReason` and
   all quotes for audit.
4. **`project_code` is unique per company, not globally** — FOXD prices
   the same project to several builders, so the same code legitimately
   appears once per builder.
5. **Hard `DELETE` on an opportunity requires it to be archived first**
   (400 otherwise), so the archive event is always in the activity feed
   even if the row is later destroyed.
6. **The activity log is append-only** for everyone except directors.
7. **Authorisation lives only in `permissions.py` (what you may do) and
   `services/scoping.py` (which rows you may see).** Never re-implement
   either rule inline in a view, and never trust the frontend for it.
8. **Every viewset's `get_queryset` goes through `scoping.scoped_*()`** —
   never `Model.objects` directly. Dashboard and report services do the
   same, which is how role visibility reaches them for free.

## Conventions to follow

- **Serializer shape:** writable relations stay plain FK ids; the nested
  read-only representation sits beside them under `<field>_detail`
  (`company_detail`, `estimator_detail`, `opportunity_detail`, ...).
  Keep this — the frontend depends on both halves.
- **`project_id` is a read-only JSON alias for `project_code`.** The DB
  column stays `project_code` to avoid colliding with Django's integer
  `id`. Writes use `project_code`.
- **Activity logging is driven from the DRF viewset lifecycle**
  (`perform_create`, `perform_update`, custom actions) — *not* model
  signals. Consequence, and it is intentional: changes made in the Django
  admin or `manage.py shell` produce **no** activity entries.
- **Business logic belongs in `services/`.** Views stay thin: resolve the
  user, call the service, return the result.
- **Money is `Decimal` and serialises as a string** (`FoxdJSONRenderer`).
  Never let a money value reach JSON as a float.
- **Automation is logged at INFO with greppable prefixes**
  (`quote_automation:`, `followup_automation:`, `followup_complete:`) so
  production can prove a trigger fired. Preserve that when editing.
- Multi-step writes are wrapped in `transaction.atomic()`.

## Known drift and traps

- **The README's auth section is stale.** It documents session + CSRF
  auth and says "no JWT"; the code has used **SimpleJWT as the primary
  frontend auth** since commit `37de8c5` (session auth is kept only for
  the Django admin and DRF browsable API). Trust `config/settings.py`
  and `apps/users/views.py` over the README.
- **`/api/loss-reason-choices/` and `/api/loss-reasons/options/` are the
  same view.** Both exist for frontend compatibility. In
  `apps/pipeline/urls.py`, `extra_patterns` **must** stay before
  `router.urls` — otherwise the DRF router captures `options` as a
  loss-reason pk and returns 404.
- **`reopen` does not re-run quote automation**, by design: existing
  pricing history is left untouched.
- **`scoped_loss_reasons` returns nothing for `project_manager`**, even
  though a PM can see won opportunities. An asymmetry, not obviously
  intentional — check before relying on it.
- **`read_only` role sees every row.** Only `project_manager` is
  row-restricted (to `stage=won`). The `read_only` restriction is on
  writes, via the permission classes.
- Cross-site cookie settings (`SameSite=None`, `Secure=True`) are set
  **unconditionally**, not gated on `DEBUG`, deliberately — so the policy
  can't break because `DEBUG` was flipped wrong at deploy time.
- Git history contains **duplicated commits** (e.g. "Fix page_size query
  param", "Fix activity note creation" each appear twice) — merge
  artefacts between `claude/foxd-tender-backend-NiPeb` and
  `CRM-Backend`. Not a bug; just don't read it as two separate fixes.

## Where to look next

- `docs/ARCHITECTURE.md` — the full model graph with every FK and
  `on_delete` behaviour, the complete API surface, the permission matrix,
  the scoping matrix, and the automation trigger flows.
- `docs/DECISIONS.md` — a dated, commit-linked log of every significant
  design decision and the problem it solved. This is the closest thing to
  the lost conversation.
