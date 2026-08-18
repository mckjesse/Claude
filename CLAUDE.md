# ⚠️ You are on the wrong branch

`CRM-Backend` is a **stale mirror** of the FOXD Tender Pipeline backend.
Do not base work here.

**The live branch is `claude/foxd-tender-backend-NiPeb`.** That is what the
FOXD Render service builds and serves, and it is where all work belongs:

```bash
git checkout claude/foxd-tender-backend-NiPeb
```

Full orientation — architecture, invariants, conventions and the decision
log — lives in `CLAUDE.md` and `docs/` **on that branch**.

## Why this branch is stale

Until 15 July 2026 work was merged from `claude/foxd-tender-backend-NiPeb`
into `CRM-Backend`, and the git history shows three such merges. That
pattern then stopped, but development continued on the feature branch and
was never merged back. As a result this branch is missing real production
work, including:

- the Mark Won workflow and migration `0011` (`award_date`) — so **this
  branch's schema does not match production**
- the `api.foxd.co` / `crm.foxd.co` production domain configuration
- terminal follow-up clearing, and the wrapped `mark_won` / `mark_lost`
  response shape

It also carries a superseded version of an August 2026 bug-fix pass, and
some accidentally committed `.pyc` files that the live branch removed.

Nothing here is deployed. Kept only as history.
