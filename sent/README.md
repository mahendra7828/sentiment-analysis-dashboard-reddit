# Reddit Sentiment Dashboard

Streamlit dashboard for Reddit post comment sentiment analysis. Paste a Reddit post URL or post ID, and the app fetches public Reddit comments, classifies them as positive, neutral, or negative with VADER sentiment scoring, and shows metrics, charts, common words, and a comment table.

## Features

- Analyze comments from a Reddit post URL or post ID.
- Search posts inside a subreddit and analyze a selected post.
- Works without Reddit API credentials for public posts.
- Positive, neutral, and negative sentiment summary.
- Plotly charts for sentiment mix, comment score distribution, and common words.
- CSV download for analyzed comments.

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Run the dashboard.

```powershell
streamlit run app.py
```

Open the local URL shown by Streamlit, usually <http://localhost:8501>.

Paste any public Reddit post link and click `Analyze`.

## Optional Reddit Credentials

Direct post-link analysis works without credentials. If you want to use your own Reddit API app/user agent, create an app at <https://www.reddit.com/prefs/apps> with type `script`, then configure `.env`.

```powershell
Copy-Item .env.example .env
```

Update `.env`:

```text
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=sentiment-dashboard/1.0 by your_reddit_username
```

## Project Structure

```text
.
|-- app.py
|-- data/
|   `-- sample_comments.csv
|-- src/
|   |-- config.py
|   |-- reddit_client.py
|   |-- sentiment.py
|   `-- visuals.py
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Notes

- The app uses public Reddit JSON endpoints when credentials are missing.
- When credentials are configured, the app can use PRAW/OAuth access.
- VADER works well for short social-media comments and does not need a model download.
- Reddit API rate limits still apply, so keep comment and post limits reasonable.
