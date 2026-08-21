# WORKING-LOCALLY.md — cloning the estate and the workflow to use

Written 21 August 2026, when the estate moved from browser-and-Lovable work
to local checkouts pushed to GitHub. Companion to `REPO-MAP.md`, which
explains what each repository *is*; this one covers how to work in them.

## The layout

One folder per repository, all under `~/Developer`:

```
~/Developer/
  CRM-backend/            the Tender Pipeline API      private
  CRM-web/                its React frontend           private   ← Lovable
  foxd-website/           the public FOXD site         private   ← Lovable
  merrigums/              merrigums.com.au             private   ← Lovable
  foxd-tool-inventory/    plant & equipment tracking   public
  foxd-apps/              six single-file tools        public
  COD/                    Black Ops randomiser         public
  Claude/                 this archive + the maps      public
```

Not worth cloning: `FOXD` (empty) and `CRM-Backend-snapshot-2026-04` (a dead
single-commit snapshot kept only because its history exists nowhere else).

## One-time setup

**GitHub Desktop** (desktop.github.com) is the least friction if you do not
live in a terminal: it installs git, signs you in — which is what makes the
four private repos clonable — and gives you Pull and Push buttons. Clone each
repo with **File → Clone repository → GitHub.com**, setting the local path to
`~/Developer/<repo-name>`.

Or from a terminal:

```bash
xcode-select --install                  # git, if you do not have it
brew install gh && gh auth login        # GitHub.com → HTTPS → login with browser

mkdir -p ~/Developer && cd ~/Developer
for r in CRM-backend CRM-web foxd-website merrigums \
         foxd-tool-inventory foxd-apps COD Claude; do
  gh repo clone "mckjesse/$r"
done
```

`gh auth login` is the load-bearing step. A plain `git clone` fails on the
four private repositories.

## The workflow

For every repo **except the three Lovable ones**:

```bash
git pull                             # start of session, always
git checkout -b feat/short-name      # a branch per change
# ...work...
git add -A && git commit -m "why, not just what"
git push -u origin feat/short-name   # then open a PR on GitHub and merge it
```

Then delete the branch. A branch is a temporary home for a change, never a
permanent home for a project — using them the other way round is what
produced the fourteen-app repository this file sits in.

Committing directly to `main` is fine for a typo in a README. It is not fine
for `CRM-backend`; see below.

## Three things that will bite you

### 1. On `CRM-backend`, reaching `main` means deploying

Render builds production from `CRM-backend` `main` with **Auto-Deploy: After
CI Checks Pass**. So merging a pull request into `main` *is* a release — CI
gates it, but nothing else does. Work on a branch; let the PR merge be the
deliberate moment you ship.

`entrypoint.sh` runs `migrate --noinput` on every deploy, so a merge carrying
a new migration changes the production schema. Run
`python manage.py makemigrations --check --dry-run` before you open the PR to
know whether one is in flight.

### 2. Three repos are also written to by Lovable

`CRM-web`, `foxd-website` and `merrigums` are Lovable projects.
`lovable-dev[bot]` pushes to them whenever you edit in Lovable. If you change
the same file locally and in Lovable, you get a conflict.

- **`git pull` before touching them locally**, every time.
- Pick one place per session — Lovable *or* local, not both.
- If you do get a conflict, the safe move is usually to take Lovable's
  version and redo your local change on top, because Lovable's copy is what
  its editor will keep re-pushing.

### 3. `.env` files are not in git, deliberately

`CRM-backend` and `foxd-tool-inventory` each ship `.env.example`. Copy it to
`.env` and fill in real values or nothing runs locally:

```bash
cp .env.example .env
```

`foxd-tool-inventory` needs one in **both** `backend/` and `frontend/`, and
both want real Entra ID tenant and client IDs from the Azure portal.

`CRM-web`'s `.env` files *are* committed, and that is correct — they hold
only the API base URL, which ships to the browser anyway. `.env` is the dev
and Lovable-preview value; `.env.production` is what the deployed build uses.
They are meant to differ.

## Per-repo notes

| Repo | Runs how | Watch for |
|---|---|---|
| `CRM-backend` | `pip install -r requirements.txt`, `manage.py migrate`, `runserver`. Needs PostgreSQL. 160 tests: `manage.py test` | Merging to `main` deploys |
| `CRM-web` | `npm install && npm run dev` | Lovable also pushes here |
| `foxd-website` | `npm install && npm run dev` | Lovable also pushes here; live public site |
| `merrigums` | `npm install && npm run dev` | Lovable also pushes here; live public site |
| `foxd-tool-inventory` | Two terminals — Django on 8000, Vite on 5173. No test suite | `.env` needed in both halves |
| `foxd-apps` | Open any `<tool>/index.html` in a browser | Nothing to build; Netlify serves the root |
| `COD` | Open `index.html` | Nothing to build |
| `Claude` | Nothing to run | Archive only. Never commit app code here again |

## The rules worth keeping

- **One repository per deployable thing.** If it deploys, or someone uses it
  on its own, it is a repo — never a branch.
- **`main` is the truth in every repo**, and is the default branch.
- **Branches are short-lived and named for the change** — `feat/award-date`,
  `fix/csv-import`, `chore/bump-django`. Delete on merge.
- **Merge pull requests; do not close them.** All four PRs in the old
  monorepo were closed unmerged, which is exactly how its backend ended up
  forked three ways.
- **`.gitignore` before the first commit** — `__pycache__/`, `*.pyc`,
  `.env`, `db.sqlite3`, `node_modules/`.
- **Set repository visibility at creation, not afterwards.** Two repos in
  this estate were created public by accident and only caught by checking.
- **A `CLAUDE.md` in every repo root**, kept honest. The one in
  `CRM-backend` spent months telling readers that pushing did not deploy
  while every push was a production release. A confidently wrong document is
  worse than none.
