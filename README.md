# StockWorkflow – Automated Stock Tracker Website

A fully automated, data-driven static website that displays your stock watchlist with current quotes, daily changes, and a 30-day historical chart. The site is deployed to GitHub Pages and updated hourly via GitHub Actions.

## What This Project Does
- Generates `site/data.json` using Python with `yfinance` (current price, open, company name) and Alpha Vantage (30-day daily closes).
- Renders a responsive Tailwind + Chart.js dashboard at `site/index.html`.
- Triggers email alerts when any stock moves more than ±2% from the day's open.
- Deploys the `site/` directory to the `gh-pages` branch using GitHub Actions.

## Repository Layout
- `site/index.html`: Single-file dashboard consuming `data.json` and rendering charts.
- `scripts/update_data.py`: Fetches data and produces `site/data.json` and optional `site/alert_content.txt`.
- `watchlist.txt`: One ticker per line (pre-filled with AAPL, MSFT, GOOGL, TSLA).
- `.github/workflows/stock_tracker.yml`: CI workflow that builds data, deploys site, and sends email alerts.
- `requirements.txt`: Python dependencies.

## Quick Start – Create Your Repository
1. Create a new GitHub repository (public or private).
2. Copy this entire folder's contents into the new repo root (preserving paths).
3. Commit and push to your default branch (often `main`).

```bash
# from the project root
git init
git add .
git commit -m "Initial commit: stock tracker site"
# add your GitHub remote and push
```

## Required GitHub Secrets
Set the following repository secrets (Settings → Secrets and variables → Actions → New repository secret):
- `ALPHA_VANTAGE_KEY`: Your Alpha Vantage API key. Get one at `https://www.alphavantage.co/support/#api-key`.
- `MAIL_USERNAME`: Your email address used for SMTP login (Gmail supported). Also used as the recipient by default.
- `MAIL_PASSWORD`: Your email password or app-specific password (for Gmail, create an App Password).

Optional: If you want to send to a different recipient, edit the workflow `to:` field.

## Enable GitHub Pages
1. Go to Repository Settings → Pages.
2. Set **Build and deployment → Source** to "Deploy from a branch".
3. Set **Branch** to `gh-pages` and **/ (root)**.
4. Save. After the first deployment, your site will be available at `https://<your-username>.github.io/<repo-name>/`.

## Run the Workflow Manually (First Deployment)
1. Push your repository with this code.
2. Go to the Actions tab in GitHub.
3. Select "Stock Tracker" workflow and click "Run workflow".
4. The workflow will:
   - Build data with `scripts/update_data.py` (needs `ALPHA_VANTAGE_KEY`).
   - Upload the `site/` artifact.
   - Deploy it to `gh-pages`.
   - If any alerts were generated, send an email via Gmail SMTP.

## How Data Updates Work
- The workflow runs hourly via cron and can be triggered on demand.
- `scripts/update_data.py` reads tickers from `watchlist.txt`.
- It collects:
  - Current price, open, and company name via `yfinance`.
  - 30-day daily close series via Alpha Vantage (free tier is rate-limited).
- Output JSON structure (written to `site/data.json`):

```json
{
  "lastUpdated": "YYYY-MM-DD HH:MM:SS UTC",
  "stocks": [
    {
      "ticker": "AAPL",
      "companyName": "Apple Inc.",
      "currentPrice": 150.25,
      "dayChange": 1.2,
      "dayChangePercent": 0.81,
      "historicalData": [145.1, 146.2, ...]
    }
  ]
}
```

- Alerts are generated when `(current - open) / open * 100` is greater than `2.0` or less than `-2.0`. These are written to `site/alert_content.txt` only if any exist.

## Local Testing (Optional)
You can run the data script locally to validate setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ALPHA_VANTAGE_KEY=your_key_here
python scripts/update_data.py
```

Then open `site/index.html` in a browser. If your browser blocks `fetch('data.json')` on a file URL, serve it locally:

```bash
python -m http.server -d site 8000
# then open http://localhost:8000
```

## Customization
- Edit `watchlist.txt` to add/remove tickers (one per line).
- Tweak the chart style in `site/index.html` (Chart.js dataset config).
- Adjust alert thresholds in `scripts/update_data.py` if desired.

## Notes on API Limits and Data Quality
- Alpha Vantage free tier limits requests per minute/day; the script sleeps briefly between requests.
- `yfinance` metadata may occasionally be missing; the script falls back to history endpoints when necessary.

## Security Considerations
- Never commit secrets. Use GitHub Actions Secrets as described above.
- For Gmail, use an App Password (recommended) instead of your real password.

---

Happy tracking!
