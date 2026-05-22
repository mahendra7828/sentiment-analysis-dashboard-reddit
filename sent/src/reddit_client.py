from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import praw
from prawcore.exceptions import NotFound, PrawcoreException, ResponseException
import requests

from src.config import RedditSettings


POST_ID_PATTERN = re.compile(r"(?:reddit\.com)?/r/[^/]+/comments/([a-z0-9]+)", re.IGNORECASE)
DEFAULT_USER_AGENT = "sentiment-dashboard/1.0"
REDDIT_BASE_URL = "https://www.reddit.com"


@dataclass(frozen=True)
class RedditPost:
    id: str
    title: str
    subreddit: str
    author: str
    score: int
    num_comments: int
    permalink: str
    url: str
    created_at: datetime


@dataclass(frozen=True)
class RedditComment:
    id: str
    body: str
    author: str
    score: int
    permalink: str
    created_at: datetime


def create_client(settings: RedditSettings) -> praw.Reddit:
    return praw.Reddit(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        user_agent=settings.user_agent,
        check_for_async=False,
    )


def extract_submission_id(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Post URL ya Reddit post ID enter karein.")

    match = POST_ID_PATTERN.search(cleaned)
    if match:
        return match.group(1)

    if re.fullmatch(r"[a-z0-9]{5,10}", cleaned, re.IGNORECASE):
        return cleaned

    raise ValueError("Valid Reddit post URL ya post ID enter karein.")


def search_posts(
    reddit: praw.Reddit | None,
    subreddit_name: str,
    query: str,
    sort: str,
    limit: int,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list[RedditPost]:
    subreddit_name = subreddit_name.strip()
    if not subreddit_name:
        raise ValueError("Subreddit name enter karein.")

    if reddit is None:
        return _search_posts_public(subreddit_name, query, sort, limit, user_agent)

    try:
        subreddit = reddit.subreddit(subreddit_name)
        if query.strip():
            submissions = subreddit.search(query.strip(), sort=sort, limit=limit)
        else:
            submissions = getattr(subreddit, sort)(limit=limit)
        return [_post_from_submission(submission) for submission in submissions]
    except (NotFound, ResponseException, PrawcoreException) as exc:
        raise RuntimeError(f"Reddit se posts fetch nahi ho paaye: {exc}") from exc


def fetch_post(
    reddit: praw.Reddit | None,
    submission_id: str,
    user_agent: str = DEFAULT_USER_AGENT,
) -> RedditPost:
    if reddit is None:
        post, _comments = _fetch_submission_json(submission_id, limit=1, user_agent=user_agent)
        return _post_from_json(post)

    try:
        submission = reddit.submission(id=submission_id)
        submission.title
        return _post_from_submission(submission)
    except (NotFound, ResponseException, PrawcoreException) as exc:
        raise RuntimeError(f"Reddit post fetch nahi ho paaya: {exc}") from exc


def fetch_comments(
    reddit: praw.Reddit | None,
    submission_id: str,
    limit: int,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list[RedditComment]:
    if reddit is None:
        _post, comments = _fetch_submission_json(submission_id, limit=limit, user_agent=user_agent)
        return list(_comment_rows_json(comments, limit))

    try:
        submission = reddit.submission(id=submission_id)
        submission.comments.replace_more(limit=0)
        comments = submission.comments.list()
        return list(_comment_rows(comments[:limit]))
    except (NotFound, ResponseException, PrawcoreException) as exc:
        raise RuntimeError(f"Reddit comments fetch nahi ho paaye: {exc}") from exc


def _post_from_submission(submission: object) -> RedditPost:
    return RedditPost(
        id=submission.id,
        title=submission.title,
        subreddit=str(submission.subreddit),
        author=str(submission.author) if submission.author else "[deleted]",
        score=int(submission.score),
        num_comments=int(submission.num_comments),
        permalink=f"https://www.reddit.com{submission.permalink}",
        url=str(submission.url),
        created_at=_utc_datetime(submission.created_utc),
    )


def _search_posts_public(
    subreddit_name: str,
    query: str,
    sort: str,
    limit: int,
    user_agent: str,
) -> list[RedditPost]:
    if query.strip():
        response = _reddit_get(
            f"/r/{subreddit_name}/search.json",
            user_agent=user_agent,
            params={
                "q": query.strip(),
                "restrict_sr": "1",
                "sort": sort,
                "limit": str(limit),
                "raw_json": "1",
            },
        )
    else:
        response = _reddit_get(
            f"/r/{subreddit_name}/{sort}.json",
            user_agent=user_agent,
            params={"limit": str(limit), "raw_json": "1"},
        )

    children = response.get("data", {}).get("children", [])
    return [_post_from_json(child["data"]) for child in children if child.get("kind") == "t3"]


def _fetch_submission_json(
    submission_id: str,
    limit: int,
    user_agent: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    response = _reddit_get(
        f"/comments/{submission_id}.json",
        user_agent=user_agent,
        params={"limit": str(limit), "raw_json": "1", "sort": "confidence"},
    )

    if not isinstance(response, list) or len(response) < 2:
        raise RuntimeError("Reddit response ka format expected nahi hai.")

    post_children = response[0].get("data", {}).get("children", [])
    if not post_children:
        raise RuntimeError("Reddit post nahi mila. Link ya post ID check karein.")

    comment_children = response[1].get("data", {}).get("children", [])
    return post_children[0]["data"], comment_children


def _reddit_get(
    path: str,
    user_agent: str,
    params: dict[str, str],
) -> object:
    try:
        response = requests.get(
            f"{REDDIT_BASE_URL}{path}",
            headers={"User-Agent": user_agent or DEFAULT_USER_AGENT},
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise RuntimeError(f"Reddit se data fetch nahi ho paaya. HTTP status: {status_code}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Reddit se data fetch nahi ho paaya: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Reddit response JSON parse nahi ho paaya.") from exc


def _post_from_json(data: dict[str, object]) -> RedditPost:
    permalink = str(data.get("permalink", ""))
    return RedditPost(
        id=str(data.get("id", "")),
        title=str(data.get("title", "Untitled Reddit post")),
        subreddit=str(data.get("subreddit", "")),
        author=str(data.get("author") or "[deleted]"),
        score=int(data.get("score") or 0),
        num_comments=int(data.get("num_comments") or 0),
        permalink=f"{REDDIT_BASE_URL}{permalink}" if permalink.startswith("/") else permalink,
        url=str(data.get("url") or ""),
        created_at=_utc_datetime(float(data.get("created_utc") or 0)),
    )


def _comment_rows(comments: Iterable[object]) -> Iterable[RedditComment]:
    for comment in comments:
        body = getattr(comment, "body", "")
        if not body or body in {"[deleted]", "[removed]"}:
            continue

        yield RedditComment(
            id=comment.id,
            body=body,
            author=str(comment.author) if comment.author else "[deleted]",
            score=int(comment.score),
            permalink=f"https://www.reddit.com{comment.permalink}",
            created_at=_utc_datetime(comment.created_utc),
        )


def _comment_rows_json(
    comments: Iterable[dict[str, object]],
    limit: int,
) -> Iterable[RedditComment]:
    yielded = 0
    for item in comments:
        if yielded >= limit:
            return

        if item.get("kind") != "t1":
            continue

        data = item.get("data", {})
        if not isinstance(data, dict):
            continue

        body = str(data.get("body") or "")
        if not body or body in {"[deleted]", "[removed]"}:
            continue

        permalink = str(data.get("permalink", ""))
        yielded += 1
        yield RedditComment(
            id=str(data.get("id", "")),
            body=body,
            author=str(data.get("author") or "[deleted]"),
            score=int(data.get("score") or 0),
            permalink=f"{REDDIT_BASE_URL}{permalink}" if permalink.startswith("/") else permalink,
            created_at=_utc_datetime(float(data.get("created_utc") or 0)),
        )

        replies = data.get("replies")
        if isinstance(replies, dict):
            reply_children = replies.get("data", {}).get("children", [])
            for reply in _comment_rows_json(reply_children, limit - yielded):
                if yielded >= limit:
                    return
                yielded += 1
                yield reply


def _utc_datetime(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
