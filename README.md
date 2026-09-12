# GitHub Activity Dashboard

A local dashboard of your GitHub activity (commits on **every** branch, plus PRs,
issues, and reviews), grouped by organization/repo, with a clickable
contribution-style heatmap. Unlike the GitHub profile page, this counts commits
on non-default branches too.

Runs entirely on your machine: a FastAPI backend pulls data from the GitHub
REST API using a personal access token and caches it in a local SQLite file;
a React frontend renders it.

## First-time setup

1. Create a classic personal access token at
   https://github.com/settings/tokens with the `repo` and `read:org` scopes.
2. Backend:
   ```bash
   cd backend
   python -m venv venv   # or specify version (3.14 does not work currently) as `py -3.12 -m venv venv`
   venv/Scripts/activate   # on macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env    # then edit .env and paste in your token
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

## Running it

After the one-time `npm run build`, day-to-day usage is just:

```bash
cd backend
venv/Scripts/activate
uvicorn app.main:app
```

Then open http://localhost:8000 and click **Sync now** to pull your activity.

### Development mode

To iterate on the frontend with hot reload, run the backend as above and, in
a second terminal:

```bash
cd frontend
npm run dev
```

Open the Vite dev server URL (usually http://localhost:5173) — it proxies
`/api` requests to the backend on port 8000.

## Using the dashboard

- **Heatmap**: click a day square to filter everything below to that day;
  click it again (or the "Clear day filter" button) to remove the filter,
  or click a different day to switch to it. Color intensity and the day
  counts always reflect whichever sidebar filters are active.
- **Date range**: presets (30/90/180/365 days) or custom since/until dates.
- **Organizations**: checkboxes to include/exclude activity by org (or your
  personal account, which is grouped the same way).
- **Include private repos**: toggle private-repo activity on/off.
- **Include non-default-branch commits**: on by default, so commits that
  only ever landed on a non-default branch (feature branches, unmerged
  work, etc.) are included — the exact gap this tool exists to fill, since
  GitHub's own profile graph only counts default-branch commits. Turn it
  off to exclude them and see only default-branch commits. This toggle
  only affects commits; PRs, issues, and reviews are unaffected by it.
- Groups are expandable: click an org or repo heading to collapse/expand it.

## How syncing works

- The first sync scans the last `DEFAULT_LOOKBACK_DAYS` (default 365, set in
  `.env`) across every branch of every repo you can access, plus your
  authored PRs/issues and reviewed PRs.
- Every sync after that is incremental: each repo only re-scans branches
  whose tip commit has moved since the last sync, and searches only cover
  the time since the last sync. Data accumulates in `backend/activity.db`,
  so the dashboard stays fast even with a lot of history.
- To change the historical lookback window, delete `backend/activity.db`,
  adjust `DEFAULT_LOOKBACK_DAYS` in `.env`, and sync again.

## Notes / limitations

- Review activity is timestamped by the reviewed PR's `updated_at` (an
  approximation of the exact review submission time), since fetching precise
  review timestamps would require an extra API call per PR.
- The heatmap coloring and day-count both reflect whatever org/private-repo
  filters are currently active in the sidebar.
- All filtering (day click, org checkboxes, private toggle) happens
  client-side against already-fetched data, so it's instant — no need to
  re-sync to change filters or the date range (as long as the range is
  within what's already been synced).
