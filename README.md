# Whoop -> Notion + Dashboard Sync

Hourly Python pipeline that syncs yesterday's Whoop data into:

- Notion workouts database (one row per workout)
- `data/data.json` append-only health history (for dashboard)

The dashboard is served by GitHub Pages and can be embedded in Notion.

## Project structure

```
whoop-notion-sync/
├── .github/workflows/sync.yml
├── src/
│   ├── whoop.py
│   ├── notion.py
│   ├── health_json.py
│   ├── github_whoop_secret.py
│   └── main.py
├── scripts/
│   └── get_token.py
├── data/
│   └── data.json
├── dashboard/
│   └── index.html
├── .env.example
├── requirements.txt
└── README.md
```

## Data flow

- `GET /activity/workout` -> upsert workout rows in Notion
- `GET /recovery`, `GET /activity/sleep`, `GET /cycle` -> upsert one daily record in `data/data.json`

The workflow runs every hour (UTC) and can also be triggered manually. GitHub may delay scheduled runs slightly under load.

Sync targets **yesterday in your local calendar** (default timezone `America/New_York`). WHOOP API windows use that full local day converted to UTC.

## Environment variables

Set these as GitHub Actions secrets and locally for manual runs:

- `WHOOP_CLIENT_ID`
- `WHOOP_CLIENT_SECRET`
- `WHOOP_REFRESH_TOKEN`
- `WHOOP_SYNC_TZ` (optional, default `America/New_York`) — IANA timezone for which calendar day counts as “today” / “yesterday”
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`

### GitHub Actions only (WHOOP refresh rotation)

WHOOP returns a **new** refresh token whenever you refresh an access token. The sync job updates the `WHOOP_REFRESH_TOKEN` repository secret automatically using the GitHub CLI, so cron runs keep working.

Add one more secret:

- `GH_REPO_PAT` — a [fine-grained personal access token](https://github.com/settings/tokens?type=beta) with access to this repo only. Under **Repository permissions**, set **Secrets** to **Read and write** (this covers `PUT .../actions/secrets/...`). The default `GITHUB_TOKEN` cannot change repository secrets. A **classic** PAT with the `repo` scope also works.

## Notion workout schema

Expected properties in your Notion database:

- `Date` (date)
- `Sport` (select)
- `Strain` (number)
- `Start Time` (rich text)
- `End Time` (rich text)

Idempotency behavior:

- Existing workout is detected by `Date == yesterday` and `Start Time == workout start`
- Existing row is updated, otherwise a new row is created

## Local setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Export environment variables (or use your own dotenv workflow)
3. Run:

   ```bash
   python src/main.py
   ```

## Get initial Whoop refresh token (one-time)

```bash
export WHOOP_CLIENT_ID=...
export WHOOP_CLIENT_SECRET=...
python scripts/get_token.py
```

This starts a local callback server at `http://localhost:8000/callback`, opens Whoop OAuth, and prints the refresh token for `WHOOP_REFRESH_TOKEN`.

## GitHub Actions

Workflow file: `.github/workflows/sync.yml`

- schedule: `0 * * * *`
- permissions: `contents: write` (required for committing `data/data.json`)

After each run, workflow commits updated `data/data.json` only when it changed.

## GitHub Pages

Enable Pages for this repo:

- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/ (root)`

Dashboard URL:

- `https://<your-username>.github.io/whoop-notion-sync/dashboard/`

Embed this URL in a Notion `/embed` block.
