# Architecture — FOXD Tender Pipeline backend

Every relationship, rule and flow in the codebase, in one place. Written
to let a session with no prior context act on this repo safely.

Companion documents: `../CLAUDE.md` (orientation + invariants),
`DECISIONS.md` (why each of these choices was made).

---

## 1. The model graph

Six domain models in `apps/pipeline/models.py`, plus the custom user in
`apps/users/models.py`. `TimestampedModel` is an abstract base adding
`created_at` / `updated_at`; `ActivityLog` deliberately opts out of it
(it only ever needs `created_at`).

```
                          ┌───────────────┐
                          │    AppUser    │  apps.users (AbstractUser)
                          │  + role       │  director | estimator |
                          │  + display_name│  project_manager | admin |
                          └───────┬───────┘  read_only  (default read_only)
                                  │
        ┌───────────────┬─────────┼──────────┬──────────────┬─────────────┐
        │ account_owner │estimator│assigned_ │assigned_to_  │created_by_  │
        │ SET_NULL      │SET_NULL │user      │user PROTECT  │user SET_NULL│
        │               │         │SET_NULL  │              │             │
        ▼               ▼         ▼          ▼              ▼             │
┌───────────────┐    ┌──────────────────┐  ┌──────────────┐  ┌───────────────┐
│    Company    │    │   Opportunity    │  │ FollowUpTask │  │  ActivityLog  │
│ (reference +  │◀───┤ company PROTECT  │◀─┤ opportunity  │  │ opportunity   │
│  account mgmt)│    │                  │  │   CASCADE    │  │   CASCADE     │
└───────┬───────┘    │                  │  │              │  └───────────────┘
        │            │                  │  │ related_quote│         ▲
        │ contacts   │                  │  │  SET_NULL ───┼─────┐   │
        │ CASCADE    │                  │  │              │     │   │
        ▼            │                  │  │ completed_by │     │   │
┌───────────────┐    │                  │  │  SET_NULL    │     │   │
│    Contact    │◀───┤ primary_contact  │  └──────────────┘     │   │
│               │    │   SET_NULL       │                       │   │
└───────────────┘    │                  │  ┌──────────────┐     │   │
                     │                  │◀─┤    Quote     │◀────┘   │
                     │                  │  │ opportunity  │         │
                     │                  │  │   CASCADE    │         │
                     │                  │  └──────────────┘         │
                     │                  │                           │
                     │                  │  ┌──────────────┐         │
                     │                  │◀─┤  LossReason  │         │
                     │                  │  │ OneToOne     │         │
                     │ archived_by      │  │   CASCADE    │         │
                     │   SET_NULL ──────┼──┘              │         │
                     └──────────┬───────┘  └──────────────┘         │
                                └────────────────────────────────────┘
                                        (all activity hangs off Opportunity)
```

### 1.1 Every foreign key, and what deleting the target does

| From | Field | To | `on_delete` | Practical consequence |
|---|---|---|---|---|
| `Contact` | `company` | `Company` | **CASCADE** | Deleting a company deletes its contacts |
| `Opportunity` | `company` | `Company` | **PROTECT** | A company with opportunities **cannot** be deleted |
| `Opportunity` | `primary_contact` | `Contact` | SET_NULL | Contact removal leaves the opportunity intact |
| `Opportunity` | `estimator` | `AppUser` | SET_NULL | — |
| `Opportunity` | `assigned_user` | `AppUser` | SET_NULL | — |
| `Opportunity` | `archived_by` | `AppUser` | SET_NULL | — |
| `Company` | `account_owner` | `AppUser` | SET_NULL | — |
| `Quote` | `opportunity` | `Opportunity` | **CASCADE** | — |
| `FollowUpTask` | `opportunity` | `Opportunity` | **CASCADE** | — |
| `FollowUpTask` | `related_quote` | `Quote` | SET_NULL | Optional link |
| `FollowUpTask` | `assigned_to_user` | `AppUser` | **PROTECT** | A user with follow-ups **cannot** be deleted |
| `FollowUpTask` | `completed_by` | `AppUser` | SET_NULL | — |
| `ActivityLog` | `opportunity` | `Opportunity` | **CASCADE** | — |
| `ActivityLog` | `created_by_user` | `AppUser` | SET_NULL | Log survives user deletion |
| `LossReason` | `opportunity` | `Opportunity` | **CASCADE** (OneToOne) | At most one per opportunity |

Two PROTECTs are the ones that bite: **Company with opportunities** and
**AppUser with follow-up tasks**. Deactivate (`is_active=False`) rather
than delete users.

### 1.2 Reverse accessors (the names used in queries and `select_related`)

`Company.contacts` · `Company.opportunities` · `Opportunity.quotes` ·
`Opportunity.tasks` · `Opportunity.activity_logs` ·
`Opportunity.loss_reason` (OneToOne) · `Quote.tasks` ·
`Contact.primary_for_opportunities` · `AppUser.owned_accounts` ·
`AppUser.estimating_opportunities` · `AppUser.assigned_opportunities` ·
`AppUser.followup_tasks` · `AppUser.completed_followups` ·
`AppUser.archived_opportunities` · `AppUser.activity_logs`

`Opportunity.loss_reason` is a reverse OneToOne: use
`hasattr(opp, "loss_reason")` to test existence — Django's
`RelatedObjectDoesNotExist` subclasses `AttributeError` precisely so this
works.

### 1.3 Database constraints

- `unique_project_code_per_company` — `UniqueConstraint(project_code, company)`.
  DRF auto-derives a `UniqueTogetherValidator`, so duplicates surface as
  a 400, not a 500.
- `unique_quote_revision_per_opportunity` — `UniqueConstraint(opportunity, revision_number)`.

### 1.4 Enumerations

| Model | Field | Values |
|---|---|---|
| `AppUser` | `role` | `director`, `estimator`, `project_manager`, `admin`, `read_only` *(default)* |
| `Company` | `company_type` | `builder`, `client`, `architect`, `project_manager`, `other` *(default)* |
| `Company` | `status` | `active` *(default)*, `inactive` |
| `Company` | `account_tier` | `A`, `B`, `C` (blank allowed) |
| `Company` | `margin_quality` | `high`, `medium`, `low` (blank allowed) |
| `Contact` | `preferred_contact_method` | `email`, `phone`, `mobile` |
| `Opportunity` | `stage` | `lead` *(default)*, `invited`, `pricing`, `submitted`, `follow_up`, `negotiating`, `won`, `lost`, `withdrawn` |
| `Opportunity` | `status` | `open` *(default)*, `closed` |
| `Quote` | `quote_status` | `draft` *(default)*, `submitted`, `revised`, `withdrawn`, `accepted`, `unsuccessful` |
| `FollowUpTask` | `task_type` | `call`, `email`, `meeting`, `reminder`, `review` |
| `FollowUpTask` | `priority` | `low`, `medium` *(default)*, `high`, `critical` |
| `FollowUpTask` | `status` | `pending` *(default)*, `in_progress`, `completed`, `cancelled` |
| `LossReason` | `reason_category` | `price`, `program`, `scope`, `relationship`, `competitor`, `cancelled`, `no_response`, `project_won_other`, `other` |

`Opportunity` carries two award dates and they are not
interchangeable: `expected_award_date` is a forward-looking estimate set
while the tender is open, and `award_date` (migration `0011`) is the date
the opportunity was actually marked won.

`stage` and `status` are **two axes, not one**: `stage` is pipeline
progression and outcome, `status` is lifecycle (open/closed). The
terminal stages `won` and `lost` always force `status=closed`.

---

## 2. API surface

Mounted in `config/urls.py`: `admin/`, `api/users/` (`apps.users.urls`),
`api/` (`apps.pipeline.urls`).

### 2.1 Auth — `apps/users/urls.py`

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/users/login/` | none | Returns `{access, refresh, user:{id, username, display_name, role}}`. No CSRF — `authentication_classes = []` |
| POST | `/api/users/token/refresh/` | refresh token | SimpleJWT `TokenRefreshView`; rotation is on |
| POST | `/api/users/logout/` | required | Ends the Django session if one exists; 204 |
| GET | `/api/users/me/` | required | Current profile; works with Bearer **or** session |
| GET | `/api/users/` | required | Active users, for estimator / assignee dropdowns |
| GET | `/api/users/csrf/` | none | Sets the `csrftoken` cookie and returns it in the body. Only needed for session flows; JWT consumers can ignore it |

Token lifetimes: access **30 minutes**, refresh **7 days**, rotate on
refresh, `Authorization: Bearer <token>`.

### 2.2 Pipeline routers — `apps/pipeline/urls.py`

`DefaultRouter` registers, all full `ModelViewSet`s:

`companies` · `contacts` · `opportunities` · `quotes` · `followups` ·
`activities` · `loss-reasons`

### 2.3 Custom actions

| Method | Path | Effect |
|---|---|---|
| POST | `/api/opportunities/{id}/mark_won/` | Body `{final_awarded_value}`, optional `award_date` / `notes`. Sets `stage=won`, `status=closed`, runs quote automation, then cancels outstanding follow-ups. **400 if currently `lost`** and **400 if archived** (not a bare 404) — reopen / restore first. Returns the wrapped shape below |
| POST | `/api/opportunities/{id}/mark_lost/` | Body `{reason_category, reason_detail?, competitor_name?, price_gap_notes?}`. `update_or_create`s the `LossReason`, sets `stage=lost`, `status=closed`, runs quote automation, then cancels outstanding follow-ups. **400 if currently `won`** — reopen first. Returns the wrapped shape below |
| POST | `/api/opportunities/{id}/reopen/` | Only from `won`/`lost`. Moves to `stage=follow_up`, `status=open`. **Preserves** the LossReason and all quotes. Logs `stage_changed` + `reopened`. Does **not** run quote automation |
| POST | `/api/opportunities/{id}/archive/` | Soft delete: `archived_at=now`, `archived_by=user`. Leaves stage/status alone. 400 if already archived |
| POST | `/api/opportunities/{id}/restore/` | Clears both archive fields. 400 if not archived |
| DELETE | `/api/opportunities/{id}/` | Hard delete. **400 unless already archived.** Cascades to quotes, tasks, activity, loss reason |
| POST | `/api/opportunities/{id}/close_related_as_lost/` | Only on a **won** opportunity. Closes every *other* non-archived `open` opportunity sharing the `project_code` as lost, with `reason_category=project_won_other` and the winning builder as `competitor_name`. Returns the affected list. Never touches the won opportunity, and never touches archived rows |
| POST | `/api/followups/{id}/complete/` | `completion_notes` **required**. `schedule_next` (bool/`"true"`/`1`, default false) optionally creates a successor; `next_due_date` defaults to +14 days, `next_subject` to `"Follow up again"`, type/priority inherit |
| POST | `/api/followups/{id}/reopen/` | Completed → `pending`; clears `completed_at`/`completed_by`, **keeps** `completion_notes` |

**`mark_won` and `mark_lost` do not return a bare opportunity.** Both
wrap it, because both now sweep follow-ups:

```json
{
  "opportunity": { ...full OpportunitySerializer... },
  "cleared_followups_count": 2,
  "cleared_followup_ids": [17, 23]
}
```

Both also drop the instance's prefetch cache before serialising, via
`_fresh_data()`. `get_object()` primes that cache; quote automation then
writes a quote and the follow-up sweep cancels tasks — neither visible to
the cache. Without the reset the response reports `latest_quote: null` for
a quote it just created and keeps advertising a `next_followup` that has
already been cancelled. DRF's `UpdateModelMixin` does this for PUT/PATCH;
custom actions must do it themselves.

`archive`, `restore` and `destroy` resolve the object through
`_get_opportunity_for_archive_path()` (which passes
`include_archived=True`) because the default queryset hides archived
rows — otherwise you could never restore anything.

### 2.4 Dashboard, reports, reference data

| Path | Returns |
|---|---|
| `/api/dashboard/` | Open pipeline value, active count, quotes awaiting follow-up, overdue / due-today follow-ups, submissions due in 7 days, `opportunities_by_stage` (all stages, zero-filled), 10 most recent activities, top 5 overdue follow-ups |
| `/api/reports/pipeline-by-stage/` | Count + value per stage |
| `/api/reports/pipeline-by-estimator/` | Count + value per estimator |
| `/api/reports/overdue-followups/` | Overdue follow-up detail |
| `/api/reports/win-rate-by-estimator/` | Win rate per estimator |
| `/api/reports/win-rate-by-company/` | Win rate per company |
| `/api/reports/loss-reasons/` | Loss counts grouped by category |
| `/api/reports/stale-opportunities/?days=30` | See §5. `days` defaults to 30; non-numeric or `<1` falls back to 30 |
| `/api/loss-reason-choices/` | `[{value, label}]` for the Mark-Lost dropdown |
| `/api/loss-reasons/options/` | **Identical view**, alternate path (see `CLAUDE.md` traps) |

### 2.5 Query parameters

**Global** (`config/pagination.py` + DRF defaults): `?page=`,
`?page_size=` (default 25, **max 500**), `?search=`, `?ordering=`.

**`/api/opportunities/`** — `OpportunityFilter`: multi-choice `stage` and
`status`; `submission_due_from/to`, `expected_award_from/to`;
`min_value`/`max_value` on `estimated_contract_value`; exact
`project_code`, `company`, `estimator`, `assigned_user`, `sector`,
`tender_type`, `opportunity_source`. Plus archive visibility:

| Parameter | Result |
|---|---|
| *(unset, or any other value)* | Active only — the default |
| `?archived=true` | Archived only |
| `?archived=all` | Both |
| `?include_archived=true` | Alias for `?archived=all` |

**`/api/followups/`** — `due_from`, `due_to`, `is_overdue` (boolean
method filter that first excludes completed/cancelled), plus
`opportunity`, `assigned_to_user`, `related_quote`, `task_type`,
`priority`, `status`.

**`/api/quotes/`** — `opportunity`, `opportunity_id` (alias, so the
frontend can send either key), `quote_status`.

**`/api/companies/`** — `company_type`, `status`, `state`,
`account_tier`, `margin_quality`, `account_owner`.

**`/api/activities/`** — `opportunity`, `activity_type`, `entity_type`.

---

## 3. Authorisation — two independent layers

Layer 1 answers *"may this role perform this action?"*
(`apps/pipeline/permissions.py`). Layer 2 answers *"which rows may this
role see at all?"* (`apps/pipeline/services/scoping.py`). Both must be
satisfied. Neither is ever re-implemented inline in a view.

Directors and Django superusers bypass every rule in layer 1.

### 3.1 Permission matrix

| Resource | Read | Create / Update | Delete | Notes |
|---|---|---|---|---|
| Company | any authenticated | director, admin | director, admin | Reference data |
| Contact | any authenticated | director, admin | director, admin | Same class as Company |
| Opportunity | any authenticated | director, estimator, admin | **director only** | Admin writes are field-restricted — see §3.2 |
| ↳ `mark_won` / `mark_lost` / `reopen` / `close_related_as_lost` | — | **director, estimator only** | — | Pricing-bearing business decisions; admin excluded |
| ↳ `archive` / `restore` | — | director, estimator, admin | — | Same set that may edit |
| Quote | any authenticated | **director, estimator only** | **director only** | Admin, PM and read-only cannot write pricing |
| FollowUpTask | any authenticated | director, admin (any); estimator (relevant only) | same | See §3.3 |
| ActivityLog | any authenticated | director, estimator, admin | **director only** | **Append-only**: update/destroy blocked for all non-directors |
| LossReason | any authenticated | **director only** | director only | Normal path is `mark_lost`, which writes it server-side |

### 3.2 Admin field protection

`ADMIN_OPPORTUNITY_PROTECTED_FIELDS` in `views.py` —
`estimated_contract_value`, `estimated_margin_percent`,
`probability_percent`, `final_awarded_value`, `stage`.

A user with `role=admin` (and not superuser) touching any of these on
create or update gets a `PermissionDenied` naming the offending fields.
Admins may still edit everything else: project name and code, company,
contact, scope text, dates, assignments. Enforced in
`_enforce_admin_field_protection()` against `serializer.validated_data`,
rather than by splitting the serializer.

### 3.3 The "relevance" rule

One canonical definition, in `permissions.py`:

```python
def is_relevant_opportunity(opportunity, user):
    return (opportunity.estimator_id == user.id
            or opportunity.assigned_user_id == user.id)
```

An estimator may only create, edit or delete follow-ups on opportunities
where they are the estimator **or** the assigned user. Update/delete go
through `has_object_permission`; **create** is checked in
`FollowUpTaskViewSet.perform_create` instead, because at permission time
the object does not exist yet. If another ownership-style rule is ever
needed, change this function — do not copy it.

### 3.4 Scoping matrix (row-level visibility)

`_sees_everything()` = superuser, `director`, `estimator`, `admin`,
**`read_only`**. `project_manager` is the only row-restricted role.

| Helper | Unrestricted roles | `project_manager` | Archive handling |
|---|---|---|---|
| `scoped_opportunities` | all rows | `stage=won` only | Excludes archived unless `include_archived=True` |
| `scoped_quotes` | all rows | parent `stage=won` | Excludes rows whose opportunity is archived |
| `scoped_followups` | all rows | parent `stage=won` | Excludes rows whose opportunity is archived |
| `scoped_activity` | all rows | parent `stage=won` | **Never filters archive** — otherwise the "archived" event itself would vanish from the audit trail |
| `scoped_loss_reasons` | all rows | **none** | Excludes rows whose opportunity is archived |
| `scoped_companies` | all rows | companies with a won opportunity (`distinct()`) | n/a |
| `scoped_contacts` | all rows | contacts of those companies (`distinct()`) | n/a |

Rationale for the PM restriction: project managers run awarded jobs and
have no need to see live tender workflow or competitor pricing.

Note that `read_only` is *not* row-restricted — its constraint is that
every permission class rejects its writes.

---

## 4. Automation flows

### 4.1 Where automation is triggered

| Entry point | Fires |
|---|---|
| `OpportunityViewSet.perform_create` | `activity.opportunity_created` → `quote_automation.sync` → `followup_automation.sync(old_stage=None)` |
| `OpportunityViewSet.perform_update` | stage diff → `opportunity_stage_changed`; field diff → `opportunity_updated`; then `quote_automation.sync` → `followup_automation.sync(old_stage)` |
| `mark_won` | `opportunity_marked_won` → `quote_automation.sync` → `clear_followups_for_terminal_opportunity` |
| `mark_lost` | `opportunity_marked_lost` → `quote_automation.sync` → `clear_followups_for_terminal_opportunity` |
| `close_related_as_lost` | per related opportunity: `stage_changed` + `marked_lost` + `quote_automation.sync` |
| `reopen` | `stage_changed` + `reopened`. **No** quote automation |
| `QuoteViewSet.perform_create/update` | `quote_created` / `quote_updated` |
| `FollowUpTaskViewSet.perform_create/update` | `followup_created` / `followup_completed` (on transition) / `followup_updated` |
| `followups/{id}/complete/` | `followup_completed`, plus `followup_created` if a successor is made |
| `followups/{id}/reopen/` | `followup_reopened` |

Everything above is wrapped in `transaction.atomic()`.

### 4.2 Quote automation — `services/quote_automation.py`

**Rule:** an opportunity in an eligible stage with a positive quoting
value always has at least one Quote.

- **Eligible stages:** `pricing`, `submitted`, `won`, `lost`. Anything
  else short-circuits with `reason=ineligible_stage`.
- **Value source:** `final_awarded_value` when `stage=won` and it is set;
  otherwise `estimated_contract_value`. Missing or `<= 0` → skip.
- **Decision:** no quotes yet → create revision 1. Latest quote's
  `quoted_value_ex_gst` differs → create `latest + 1`. Value unchanged →
  skip. So unrelated edits never produce duplicate revisions.
- **Stage → quote status:** `pricing`→`draft`, `submitted`→`submitted`,
  `won`→`accepted`, `lost`→`unsuccessful`.
- **Field mapping** is one explicit dict in `_build_quote_payload()` —
  no signals, no serializer magic:

| Opportunity | → Quote |
|---|---|
| the instance | `opportunity` |
| `project_code` + `-R{revision}` | `quote_reference` |
| resolved value | `quoted_value_ex_gst` |
| `estimated_margin_percent` | `quoted_margin_percent` |
| `submission_date` | `submission_date` |
| `_STATUS_FOR_STAGE[stage]` | `quote_status` |

Every branch logs at INFO under `quote_automation:`. Two management
commands exist for this path: `prove_quote_creation` (asserts the mapping
end to end) and `backfill_quotes`.

### 4.2a Terminal follow-up clearing — `clear_followups_for_terminal_opportunity`

When an opportunity becomes terminal, every **outstanding** follow-up
(`status=pending` and `completed_at IS NULL`) is moved to `cancelled` —
**never hard-deleted** — with a completion note, timestamp and the acting
user, so the history survives. Idempotent: a repeat call finds nothing.
Returns the list of cleared ids, which both `mark_won` and `mark_lost`
surface as `cleared_followup_ids`.

The dashboard reinforces this from the other side: its pending-follow-up
queries exclude anything whose parent opportunity is terminal, so a task
that somehow stayed pending on a closed opportunity can never surface as
outstanding.

### 4.3 Follow-up automation — `services/followup_automation.py`

Fires **only on the transition into `submitted`** (`stage == submitted`
and `old_stage != submitted`).

- Duplicate guard: skips if a task with the canonical subject
  `"Follow up on submitted quote"` already exists for the opportunity —
  so the whole function is idempotent.
- Due date: `(submission_date or today) + 14 days`.
- Assignee precedence: `assigned_user` → `estimator` → the acting user.
  If all three are absent it logs a warning and creates nothing.
- Creates an `email`-type, `medium`-priority, `pending` task.

### 4.4 Follow-up completion — `POST /api/followups/{id}/complete/`

`completion_notes` is required (400 if blank). `schedule_next` is parsed
tolerantly: real bools, the strings `"true"`/`"1"`/`"yes"`, or ints —
defaulting to false, i.e. **close out for good unless asked otherwise**.

When scheduling a successor, `_create_successor` applies a duplicate
guard: nothing is created if a `pending`/`in_progress` task with the same
subject already exists on that opportunity. In that case the response
simply has no `next_followup` key.

`reopen` clears `completed_at`/`completed_by` but keeps
`completion_notes` for audit.

### 4.5 Activity log mechanics — `services/activity.py`

`snapshot(instance, FIELDS)` before the save, `diff(instance, baseline)`
after; the changed field names are run through `FIELD_LABELS` and
`_humanise()` to produce business-readable prose ("Opportunity details
updated: estimated contract value, and notes.").

Three curated tracked-field tuples — `OPPORTUNITY_TRACKED_FIELDS`,
`QUOTE_TRACKED_FIELDS`, `FOLLOWUP_TRACKED_FIELDS` — decide what counts
as a business-relevant change. **Adding a model field does not
automatically make it logged;** add it to the relevant tuple and to
`FIELD_LABELS`.

`stage` is stripped from the generic opportunity "updated" description
and `status` from the follow-up one, because each has its own dedicated
event — this is what stops double-logging a single save.

`ActivityLog.entity_type` / `entity_id` are a lightweight pointer at the
sub-object an event concerns, deliberately in place of a formal generic
relation. `ActivityLogSerializer` defaults `entity_type="opportunity"`
and `activity_type="note"`, and the viewset auto-fills `entity_id` from
the opportunity and stamps `created_by_user`, so the frontend can post a
free-text note with just `{"opportunity": id, "description": "..."}`.

---

## 5. The stale-opportunity rule

`services/reports.py`. An opportunity is stale when **all** hold:

1. not archived (`scoped_opportunities` already excludes archived rows),
2. `stage` ∈ {`submitted`, `follow_up`, `negotiating`} — never
   `won`/`lost`/`lead`,
3. at least `days` (default **30**) since its *effective submission
   date*,
4. it has **no** `pending`/`in_progress` follow-up with
   `due_date >= today`.

Effective submission date resolves by strict priority
(`_submission_date_for`, which returns `(date, is_true_submission)`):

1. `Opportunity.submission_date`
2. latest `Quote.submission_date` by revision number
3. latest **submitted** quote's `created_at`
4. `Opportunity.updated_at` — **fallback only**, and the only case where
   `is_true_submission` is `False`, so callers can treat it cautiously

Response metadata for the frontend's Close-Off panel: `stale_since_date`,
`days_since_submission`, `last_followup_date`, `next_followup_date`.
Closing off a stale opportunity uses the existing `mark_lost` action —
there is no separate endpoint.

---

## 6. Serializer conventions

**Plain FK id + `_detail` sibling.** Writable relations stay integer ids;
the nested read-only object sits beside them. Present pairs:
`company`/`company_detail`, `primary_contact`/`primary_contact_detail`,
`estimator`/`estimator_detail`, `assigned_user`/`assigned_user_detail`,
`opportunity`/`opportunity_detail`,
`assigned_to_user`/`assigned_to_user_detail`,
`account_owner`/`account_owner_detail`,
`created_by_user`/`created_by_user_detail`.

**Nested shapes.** `OpportunitySummarySerializer` is the canonical nested
opportunity used from quotes, tasks, activity logs and loss reasons:
`{id, project_name, project_id, company_name}` — where `project_id`
aliases `project_code` and `company_name` comes from the joined row, so
consumers **must** `select_related("opportunity__company")`.
`CompanyForOpportunitySerializer` widens the minimal company shape with
`primary_email` and `primary_phone` for the opportunity page only;
`OpportunityForFollowUpSerializer` adds `company_name`.

**Computed fields on `OpportunitySerializer`:** `project_id`,
`is_archived` (`archived_at is not None`), `latest_quote` (from the
prefetched `quotes`, no extra query), `next_followup` (earliest
pending/in-progress task by `(due_date, due_time)`), `loss_reason`
(category key, for grouping) and `loss_reason_detail` (full nested
summary with display label). The last two are `None` when no LossReason
exists.

**`FollowUpTaskSerializer`:** `is_overdue` is `False` for
completed/cancelled tasks, otherwise `due_date < today`.
`assigned_to_user` is explicitly `required=True, allow_null=False`. Its
`update()` auto-stamps `completed_at` on the transition to `completed`.

**Validation in `OpportunitySerializer.validate`** — the four rules that
hold the state model together, applied on **every** write path:

1. `current_stage` ∈ {`won`,`lost`} and changing → 400, pointing at
   `reopen`.
2. `stage=won` without `final_awarded_value` → 400.
3. `stage=lost` without an existing `LossReason` → 400, pointing at
   `mark_lost`.
4. Terminal stage → `attrs["status"] = closed`, unconditionally.

`validate_probability_percent` bounds it to 0–100.
`QuoteSerializer.validate_revision_number` requires `>= 1`, and exposes
read-only aliases `value` (→ `quoted_value_ex_gst`) and `submitted_at`
(→ `submission_date`).

**Action payload serializers:** `MarkWonSerializer`
(`final_awarded_value`, `min_value=0`) and `MarkLostSerializer`
(`reason_category` choice + three optional blank-allowed text fields).

---

## 7. Query performance

Each `get_queryset` fixes its own N+1s, and the nested serializers depend
on those joins being present:

| Viewset | Prefetch strategy |
|---|---|
| `CompanyViewSet` | `select_related("account_owner")` |
| `ContactViewSet` | `select_related("company")` |
| `OpportunityViewSet` | `select_related(company, primary_contact, estimator, assigned_user, loss_reason, archived_by)` + `prefetch_related(quotes, tasks)` |
| `QuoteViewSet` | `select_related(opportunity, opportunity__company)` |
| `FollowUpTaskViewSet` | `select_related(opportunity, opportunity__company, assigned_to_user, related_quote)` |
| `ActivityLogViewSet` | `select_related(opportunity, opportunity__company, created_by_user)` |
| `LossReasonViewSet` | `select_related(opportunity, opportunity__company)` |

`get_latest_quote` and `get_next_followup` iterate the **prefetched**
relations in Python rather than issuing `.order_by().first()`, which
would defeat the prefetch. Keep it that way.

---

## 8. Configuration and deployment

`config/settings.py` is single-file and env-driven via `python-dotenv`.

- `_csv()` splits comma-separated env vars **and strips trailing
  slashes** — a copy-paste artefact that silently breaks Django's
  exact-match origin comparison for CORS and CSRF.
- Database: `dj_database_url` parses `DATABASE_URL` when present and
  parseable; otherwise it falls back to the discrete `DB_*` vars. The
  fallback is deliberate hardening against an unparseable value on
  Render. `ssl_require=not DEBUG`.
- Render's injected `RENDER_EXTERNAL_HOSTNAME` is appended to
  `ALLOWED_HOSTS` and (as `https://…`) to `CSRF_TRUSTED_ORIGINS`
  automatically. The variable only exists on Render, so local dev is
  unaffected.
- Auth: `JWTAuthentication` **first**, `SessionAuthentication` second
  (admin + browsable API only). Default permission `IsAuthenticated`.
- Renderers: `FoxdJSONRenderer` then `BrowsableAPIRenderer`.
- Cookies: `SESSION_COOKIE_SAMESITE="None"`, `SECURE=True`,
  `CSRF_COOKIE_SAMESITE="None"`, `SECURE=True`, set **unconditionally**
  so the policy cannot break because `DEBUG` was flipped wrong at deploy
  time. `CSRF_COOKIE_HTTPONLY=False` so React can read the token;
  `SESSION_COOKIE_HTTPONLY=True`. Both cookie `Domain`s pinned to `None`
  so the browser scopes them to the exact backend host.
- `DEBUG=False` additionally enables `SECURE_PROXY_SSL_HEADER`
  (Render terminates TLS at the edge), HSTS (1 hour — bump once
  validated), `SECURE_CONTENT_TYPE_NOSNIFF` and
  `SECURE_REFERRER_POLICY="same-origin"`.
- Middleware order matters: `CorsMiddleware` **first** (so CORS headers
  reach redirects and static responses), then `SecurityMiddleware`, then
  `WhiteNoiseMiddleware`.
- **Production domains are baked in as a baseline, not left to env
  vars.** `api.foxd.co` and the current Render URL are merged into
  `ALLOWED_HOSTS`, and `crm.foxd.co` into the CORS/CSRF origins, on top of
  anything the env supplies — so the service keeps answering on its
  production domain even if an env var drifts or is unset. The Render URL
  and the Lovable origin are retained deliberately during the domain
  cutover and can be dropped once traffic has fully moved.
- Locale: `en-au`, `Australia/Sydney`, `USE_TZ=True`.

**Deployment:** Docker image on Render. The Dockerfile installs
requirements and runs `collectstatic` at build time; `entrypoint.sh` runs
`migrate --noinput` then `exec gunicorn config.wsgi:application`.
Migrating on container start is safe for a **single** instance — if the
service is scaled past one, move `migrate` into a Render pre-deploy
command. Health check path `/admin/login/`.

---

## 9. Migration history

`apps/users/0001_initial` creates `AppUser`. Pipeline:

| Migration | Change |
|---|---|
| `0001_initial`, `0002_initial` | Initial six models (split to resolve circular FKs) |
| `0003_alter_company_options_alter_opportunity_options` | Verbose names / ordering |
| `0004_project_code_required_unique` | `project_code` required + globally unique |
| `0005_archived_fields` | `archived_at`, `archived_by` |
| `0006_project_code_unique_per_company` | Drops the global unique index; adds the compound constraint |
| `0007_followup_completion_fields` | `completed_at`, `completed_by`, `completion_notes` |
| `0008_loss_reason_project_won_other` | Adds the `project_won_other` category |
| `0009_company_account_mgmt_fields` | Six account-management fields on `Company`; `RunSQL` drops the abandoned `accounts_*` tables |
| `0010_standardise_loss_reason_choices` | **Data migration** remapping old category values, then narrowing the choices |
| `0011_opportunity_award_date` | `award_date` — the date an opportunity was actually won |

`0004` → `0006` and `0010` are the two places where a migration changed
an existing rule rather than adding to it; see `DECISIONS.md`.

---

## 10. Tests

160 tests across 13 files. There is no pytest config — this is the Django
test runner.

| File | Tests | Covers |
|---|---|---|
| `pipeline/tests/test_opportunities.py` | 48 | CRUD, stage/status invariants, archive/restore/delete, reopen, uniqueness, Mark Won workflow, terminal-transition guards, action response freshness |
| `pipeline/tests/test_permissions.py` | 16 | The role matrix per resource |
| `pipeline/tests/test_quote_automation.py` | 15 | Eligible stages, value source, revision decisions, status mapping |
| `pipeline/tests/test_followup_completion.py` | 11 | Required notes, close-out vs successor, duplicate guard, reopen |
| `pipeline/tests/test_stale_opportunities.py` | 12 | Threshold, eligible stages, future-follow-up exclusion, date fallbacks, metadata |
| `pipeline/tests/test_terminal_followups.py` | 9 | Outstanding follow-ups cancelled (not deleted) when an opportunity goes terminal; idempotence |
| `pipeline/tests/test_reports.py` | 2 | Report shape including `award_date` |
| `pipeline/tests/test_followup_automation.py` | 9 | Transition-only firing, idempotence, assignee precedence |
| `pipeline/tests/test_close_related.py` | 9 | Grouped close, loss-reason content, response shape, idempotence, archived rows excluded, real previous stage logged |
| `pipeline/tests/test_dashboard.py` | 9 | Aggregate shape and counts, overdue-follow-up priority ordering |
| `pipeline/tests/test_followups.py` | 6 | Follow-up CRUD and filters |
| `pipeline/tests/test_quote_revisions.py` | 5 | Revision uniqueness, `opportunity_id` filter alias |
| `users/tests/test_auth.py` | 9 | JWT login, Bearer access to `/me/`, refresh, CSRF *not* required (verified with `enforce_csrf_checks=True`) |

Management commands double as executable proofs: `prove_quote_creation`
asserts the Opportunity→Quote mapping end to end, `backfill_quotes`
repairs historical rows, `seed_demo` builds a fixed-seed dataset (10
companies, 15 contacts, 25 opportunities across every stage, quotes,
follow-ups, loss reasons, backdated activity) plus five demo users —
`director`, `estimator1`, `estimator2`, `projects`, `officeadmin`, all
with password `demo12345`.
