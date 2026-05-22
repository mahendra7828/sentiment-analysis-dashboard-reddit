from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import load_reddit_settings
from src.reddit_client import (
    DEFAULT_USER_AGENT,
    create_client,
    extract_submission_id,
    fetch_comments,
    fetch_post,
    search_posts,
)
from src.sentiment import analyze_comments, common_words, summarize_sentiment
from src.visuals import score_scatter, sentiment_bar, sentiment_donut, words_bar


st.set_page_config(
    page_title="Reddit Sentiment Dashboard",
    page_icon="R",
    layout="wide",
)


def main() -> None:
    st.title("Reddit Sentiment Dashboard")

    settings = load_reddit_settings(st.secrets)
    reddit = create_client(settings) if settings else None
    user_agent = settings.user_agent if settings else DEFAULT_USER_AGENT
    query_post_value = _read_query_post_param()
    query_analyze_clicked = False
    query_selected_post_id = None

    if query_post_value and st.session_state.get("last_query_post") != query_post_value:
        try:
            query_selected_post_id = extract_submission_id(query_post_value)
            query_analyze_clicked = True
            st.session_state["last_query_post"] = query_post_value
        except ValueError as exc:
            st.error(str(exc))

    with st.sidebar:
        st.header("Reddit Source")
        source_type = st.radio("Mode", ["Post URL / ID", "Subreddit search"])
        comment_limit = st.slider("Comments", 25, 500, 150, step=25)
        min_comment_score = st.slider("Minimum comment score", -50, 200, -50)

        selected_post_id = None
        analyze_clicked = False

        if source_type == "Post URL / ID":
            post_value = st.text_input("Post URL or ID", placeholder="https://www.reddit.com/r/.../comments/...")
            analyze_clicked = st.button("Analyze post", type="primary", use_container_width=True)
            if analyze_clicked and post_value:
                try:
                    selected_post_id = extract_submission_id(post_value)
                except ValueError as exc:
                    st.error(str(exc))
            elif analyze_clicked:
                st.warning("Reddit post link ya post ID paste karein.")
        else:
            subreddit = st.text_input("Subreddit", value="python")
            query = st.text_input("Search query", value="streamlit")
            sort_options = ["relevance", "hot", "top", "new", "comments"]
            if not query.strip():
                sort_options = ["hot", "top", "new", "controversial"]
            sort = st.selectbox("Sort", sort_options, index=0)
            post_limit = st.slider("Posts to search", 5, 25, 10)
            find_clicked = st.button("Find posts", use_container_width=True)

            if find_clicked:
                with st.spinner("Fetching Reddit posts..."):
                    try:
                        st.session_state["posts"] = search_posts(
                            reddit,
                            subreddit,
                            query,
                            sort,
                            post_limit,
                            user_agent=user_agent,
                        )
                    except (RuntimeError, ValueError) as exc:
                        st.error(str(exc))
                        st.session_state["posts"] = []

            posts = st.session_state.get("posts", [])
            if posts:
                labels = [
                    f"{post.title[:80]} | r/{post.subreddit} | {post.num_comments} comments"
                    for post in posts
                ]
                selected_label = st.selectbox("Select post", labels)
                selected_index = labels.index(selected_label)
                selected_post_id = posts[selected_index].id
                analyze_clicked = st.button("Analyze selected post", type="primary", use_container_width=True)

        st.divider()
        st.caption("Credentials optional hain. Direct post links public Reddit JSON se bhi analyze ho jaate hain.")

    with st.form("main_post_form", border=False):
        post_col, button_col = st.columns([0.78, 0.22], vertical_alignment="bottom")
        with post_col:
            main_post_value = st.text_input(
                "Paste Reddit post link",
                value=query_post_value,
                placeholder="https://www.reddit.com/r/.../comments/...",
            )
        with button_col:
            main_analyze_clicked = st.form_submit_button("Analyze", type="primary", use_container_width=True)

    if query_analyze_clicked:
        analyze_clicked = True
        selected_post_id = query_selected_post_id

    if main_analyze_clicked:
        analyze_clicked = True
        try:
            selected_post_id = extract_submission_id(main_post_value)
        except ValueError as exc:
            selected_post_id = None
            st.error(str(exc))

    if analyze_clicked and selected_post_id:
        with st.spinner("Fetching comments and running sentiment analysis..."):
            try:
                post = fetch_post(reddit, selected_post_id, user_agent=user_agent)
                comments = fetch_comments(reddit, selected_post_id, comment_limit, user_agent=user_agent)
                df = analyze_comments(comments)
                st.session_state["analysis"] = {
                    "df": df,
                    "post_title": post.title,
                    "post_url": post.permalink,
                    "post_meta": post,
                }
            except RuntimeError as exc:
                st.error(str(exc))

    analysis = st.session_state.get("analysis")
    if analysis:
        render_dashboard(
            analysis["df"],
            post_title=analysis["post_title"],
            post_url=analysis["post_url"],
            min_comment_score=min_comment_score,
        )
    else:
        st.info(" paste the link of reddit post - Analyze .")


def render_dashboard(
    df: pd.DataFrame,
    post_title: str,
    post_url: str | None,
    min_comment_score: int,
) -> None:
    filtered = df[df["comment_score"] >= min_comment_score].copy()

    if filtered.empty:
        st.warning("Selected filters ke baad comments available nahi hain.")
        return

    summary = summarize_sentiment(filtered)

    title_col, link_col = st.columns([0.78, 0.22])
    with title_col:
        st.subheader(post_title)
    with link_col:
        if post_url:
            st.link_button("Open on Reddit", post_url, use_container_width=True)

    metric_cols = st.columns(5)
    metric_cols[0].metric("Comments", summary["total"])
    metric_cols[1].metric("Positive", f'{summary["positive_pct"]}%')
    metric_cols[2].metric("Negative", f'{summary["negative_pct"]}%')
    metric_cols[3].metric("Neutral", f'{summary["neutral_pct"]}%')
    metric_cols[4].metric("Avg score", summary["avg_compound"])

    chart_a, chart_b = st.columns(2)
    with chart_a:
        st.plotly_chart(sentiment_donut(filtered), use_container_width=True)
    with chart_b:
        st.plotly_chart(sentiment_bar(filtered), use_container_width=True)

    st.plotly_chart(score_scatter(filtered), use_container_width=True)

    word_col_a, word_col_b = st.columns(2)
    with word_col_a:
        st.plotly_chart(words_bar(common_words(filtered, "Positive"), "Common positive words"), use_container_width=True)
    with word_col_b:
        st.plotly_chart(words_bar(common_words(filtered, "Negative"), "Common negative words"), use_container_width=True)

    sentiment_filter = st.segmented_control(
        "Comment sentiment",
        ["All", "Positive", "Neutral", "Negative"],
        default="All",
    )
    comments_table = filtered
    if sentiment_filter != "All":
        comments_table = comments_table[comments_table["sentiment"] == sentiment_filter]

    st.download_button(
        "Download CSV",
        data=comments_table.to_csv(index=False).encode("utf-8"),
        file_name="reddit_sentiment_comments.csv",
        mime="text/csv",
    )

    st.dataframe(
        comments_table[
            ["sentiment", "compound", "comment_score", "author", "body", "permalink"]
        ].sort_values("compound", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "permalink": st.column_config.LinkColumn("Link"),
            "body": st.column_config.TextColumn("Comment", width="large"),
            "compound": st.column_config.NumberColumn("Compound", format="%.3f"),
        },
    )


def _read_query_post_param() -> str:
    value = st.query_params.get("post", "")
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value).strip()


if __name__ == "__main__":
    main()
