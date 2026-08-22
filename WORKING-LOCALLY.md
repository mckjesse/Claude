# WORKING-LOCALLY.md — cloning the estate and the workflow to use

Written 21 August 2026, when the estate moved from browser-and-Lovable work
to local checkouts pushed to GitHub. Companion to `REPO-MAP.md`, which
explains what each repository *is*; this one covers how to work in them.

## The layout

One folder per repository, all under `C:\Dev` (Windows) or `~/Developer`
(macOS):

```
C:\Dev\                   <- also Ava's Claude Code project root
  .claude\                her skills, agents, settings
  CLAUDE.md               her orientation
  CRM-backend\            the Tender Pipeline API      private
  CRM-web\                its React frontend           private   <- Lovable
  foxd-website\           the public FOXD site         private   <- Lovable
  merrigums\              merrigums.com.au             private   <- Lovable
  foxd-tool-inventory\    plant & equipment tracking   public
  foxd-apps\              six single-file tools        public
  COD\                    Black Ops randomiser         public
  Claude\                 this archive + the maps      public
```

The repos sit **inside** Ava's project root, which is deliberate — it is what
puts them in her scope. It also means the two cannot be moved independently:
see **Ava and Claude Code projects** below.

Not worth cloning: `FOXD` (empty) and `CRM-Backend-snapshot-2026-04` (a dead
single-commit snapshot kept only because its history exists nowhere else).

**Do not keep these in OneDrive, Dropbox or iCloud Drive.** A sync client
watching a repository syncs the `.git` directory too, which corrupts index
and lock files mid-operation, fights with `node_modules`, and leaves
"conflict copy" files inside the working tree. `C:\Dev` is deliberately
outside the synced user folders. The trade is that an uncommitted change now
exists in exactly one place, so push more deliberately than you would with a
sync client as a net.

## One-time setup

**GitHub Desktop** (desktop.github.com) is the least friction if you do not
live in a terminal: it installs git, signs you in — which is what makes the
four private repos clonable — and gives you Pull and Push buttons. Clone each
repo with **File → Clone repository → GitHub.com**, setting the local path to
`C:\Dev\<repo-name>`.

Or from a terminal — Windows, with [GitHub CLI](https://cli.github.com)
installed:

```powershell
gh auth login                     # GitHub.com -> HTTPS -> login with browser

New-Item -ItemType Directory -Force C:\Dev; Set-Location C:\Dev
'CRM-backend','CRM-web','foxd-website','merrigums',
'foxd-tool-inventory','foxd-apps','COD','Claude' |
  ForEach-Object { gh repo clone "mckjesse/$_" }
```

macOS:

```bash
xcode-select --install                  # git, if you do not have it
brew install gh && gh auth login

mkdir -p ~/Developer && cd ~/Developer
for r in CRM-backend CRM-web foxd-website merrigums \
         foxd-tool-inventory foxd-apps COD Claude; do
  gh repo clone "mckjesse/$r"
done
```

`gh auth login` is the load-bearing step. A plain `git clone` fails on the
four private repositories.

## Moving a checkout later

Git stores no absolute paths, so moving a repository is just moving the
folder — the remotes live inside `.git` and travel with it. GitHub Desktop,
however, stores the path: after a move every repo shows as missing, and each
needs **Locate…** (or **File → Add local repository**) pointed at the new
location.

If you use right-click → **Remove** instead, untick **"Also move to Recycle
Bin"** or it deletes the folder. Close GitHub Desktop and any editor before
moving, so nothing holds a lock on `.git`.

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

Those commands are identical in PowerShell, and GitHub Desktop does the same
things: **Current branch → New branch**, then Commit, then **Publish
branch**, then **Preview Pull Request**.

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

```powershell
Copy-Item .env.example .env     # macOS/Linux: cp .env.example .env
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

## Ava and Claude Code projects

Ava is the executive agent, and her Claude Code project root is `C:\Dev`
itself — the same folder the repositories sit in. That has consequences the
repositories do not.

### She needs to be in a repo

As of 21 Aug 2026 Ava is **local only** — no git remote. While she lived in
OneDrive that was survivable; outside it, her `CLAUDE.md`, skills, agents and
settings exist in exactly one place. Put her in a **private** repository.

Write the `.gitignore` *before* the first commit, or credentials go up with
it:

```
.env
.env.*
.venv/
node_modules/
__pycache__/
*.log
```

Then check the first commit's file list before publishing. Anything from the
Microsoft 365 or Todoist connectors is a credential.

### Moving her breaks three things, none of them obvious

**1. Claude Code keys project state by absolute path.** `~/.claude.json`
(`C:\Users\<you>\.claude.json`) holds an entry per project *directory* —
conversation history, permission grants, MCP approvals. Move the folder and
Claude Code sees a brand-new project, so all of that resets.

Her actual configuration is safe: the project's own `.claude\` directory and
`CLAUDE.md` travel with the files. Only the host-side state is path-keyed. To
carry it across, close Claude Code, **copy `.claude.json` somewhere safe**,
then change that project's key from the old path to the new one. If it goes
wrong, restore the copy — the downside is losing history, not losing Ava.

**2. Python virtual environments do not survive a move.** `pyvenv.cfg`,
`Scripts\activate` and every shebang have the old absolute path compiled in.
Delete and rebuild:

```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**3. Skills and scripts hardcode paths.** Find them before they surprise you:

```powershell
Select-String -Path C:\Dev\*,C:\Dev\.claude\* `
  -Include *.md,*.json,*.ps1,*.bat,*.py `
  -Pattern "OneDrive - Foxd Group" -Recurse |
  Select-Object Path,LineNumber,Line
```

One distinction matters in what that returns: a path pointing **into**
OneDrive for actual documents — SWMS templates, insurance certificates, the
things `project-packs` reads — is still correct and should be left alone.
OneDrive has not gone anywhere. It is only references to the old **Developer
folder** that need updating.

### And stop her before moving anything

Close the Claude Code session first. Moving files under a live agent is how
you get half-written state, and a `.git` directory mid-write is worse.

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
