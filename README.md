# The Good Climate

A small static website that shows 10–20 positive, recent news stories about
emissions reduction, sustainability, the energy transition, and the
environment more broadly. Built to be hosted for free on GitHub Pages, with
a scheduled GitHub Action that refreshes the stories automatically every
3 days — no server, database, or API key required.

## How it works

- `index.html`, `styles.css`, `app.js` — the site itself. It reads
  `data/stories.json` and renders the stories as cards, with category tabs
  and a "Favorites" tab.
- `data/stories.json` — the current list of stories. Comes pre-seeded with
  real stories so the site works the moment you publish it.
- `scripts/fetch_news.py` — searches Google News RSS (no API key needed)
  for positive stories in four categories, filters out obviously negative
  results, de-duplicates, and rewrites `data/stories.json`.
- `.github/workflows/update-news.yml` — a scheduled GitHub Action that runs
  the script every 3 days and commits the refreshed `data/stories.json`
  back to the repo automatically. You can also trigger it manually any time
  from the **Actions** tab ("Run workflow").
- **Favorites** are saved locally in each visitor's browser (`localStorage`),
  by clicking the ★ on any story. Nothing is sent to a server, so favorites
  are private to each browser/device and won't sync between devices.

## Setting it up on GitHub

1. Create a new repository on GitHub (public or private — Pages works with
   both on paid plans; public repos get Pages free).
2. Upload all the files in this folder to that repository, preserving the
   folder structure (`.github/workflows/update-news.yml` must stay in that
   exact path).
3. In the repo, go to **Settings → Pages**, and under "Build and
   deployment" set **Source** to "Deploy from a branch", branch `main`
   (or `master`), folder `/ (root)`. Save. GitHub will give you a URL like
   `https://<your-username>.github.io/<repo-name>/` within a minute or two.
4. Go to **Settings → Actions → General**, scroll to "Workflow
   permissions", and select **"Read and write permissions"**. This lets the
   scheduled Action commit the updated story file back to the repo. (Without
   this, the workflow will fail to push its update.)
5. That's it. The site is live immediately with the seeded stories, and the
   Action will refresh them automatically every 3 days at 00:00 UTC. You can
   also click **Actions → "Update good news stories" → Run workflow** any
   time to refresh it on demand.

## Customizing

- **Change the search topics or "good news" filtering**: edit the `QUERIES`
  and `NEGATIVE_SIGNAL_WORDS` lists at the top of `scripts/fetch_news.py`.
- **Change how many stories are shown**: edit `TARGET_TOTAL_MIN` /
  `TARGET_TOTAL_MAX` (default 10–20) and `MAX_PER_CATEGORY` in the same
  file.
- **Change the refresh schedule**: edit the `cron` line in
  `.github/workflows/update-news.yml` (currently `0 0 */3 * *`, i.e. every
  3 days at midnight UTC).
- **Run it locally**: `python3 scripts/fetch_news.py` (standard library
  only, no dependencies to install) will fetch fresh stories and overwrite
  `data/stories.json` — useful for testing changes before pushing.

## Notes

- The "good news" filter is a simple keyword heuristic (positive terms in
  the search query, negative terms excluded from results) — it's not
  perfect sentiment analysis, so occasionally review the results and adjust
  the keyword lists if something doesn't fit the tone you want.
- Google News RSS occasionally rate-limits automated requests. If a
  scheduled run comes up short on stories, the next run 3 days later will
  usually pick up the slack — the script always keeps whatever was already
  in `data/stories.json` if a fetch fails outright (it won't overwrite good
  data with an empty result unless the fetch actually returns content).
