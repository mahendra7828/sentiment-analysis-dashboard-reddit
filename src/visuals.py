from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


SENTIMENT_COLORS = {
    "Positive": "#1f9d55",
    "Neutral": "#6b7280",
    "Negative": "#d64545",
}


def sentiment_donut(df: pd.DataFrame) -> go.Figure:
    counts = _sentiment_counts(df)
    fig = px.pie(
        counts,
        values="count",
        names="sentiment",
        hole=0.58,
        color="sentiment",
        color_discrete_map=SENTIMENT_COLORS,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _style(fig, height=340)


def sentiment_bar(df: pd.DataFrame) -> go.Figure:
    counts = _sentiment_counts(df)
    fig = px.bar(
        counts,
        x="sentiment",
        y="count",
        color="sentiment",
        color_discrete_map=SENTIMENT_COLORS,
        text="count",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, yaxis_title="Comments", xaxis_title="")
    return _style(fig, height=340)


def score_scatter(df: pd.DataFrame) -> go.Figure:
    plot_df = df.reset_index(names="comment_index")
    fig = px.scatter(
        plot_df,
        x="comment_index",
        y="compound",
        color="sentiment",
        size=plot_df["comment_score"].clip(lower=1),
        hover_data=["author", "comment_score"],
        color_discrete_map=SENTIMENT_COLORS,
    )
    fig.add_hline(y=0.05, line_dash="dot", line_color="#1f9d55")
    fig.add_hline(y=-0.05, line_dash="dot", line_color="#d64545")
    fig.update_layout(xaxis_title="Comment order", yaxis_title="Compound sentiment")
    return _style(fig, height=360)


def words_bar(words_df: pd.DataFrame, title: str) -> go.Figure:
    if words_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No words available", x=0.5, y=0.5, showarrow=False)
        return _style(fig, height=300)

    fig = px.bar(
        words_df.sort_values("count"),
        x="count",
        y="word",
        orientation="h",
        color="count",
        color_continuous_scale=["#9ca3af", "#2563eb"],
        title=title,
    )
    fig.update_layout(yaxis_title="", xaxis_title="Mentions", coloraxis_showscale=False)
    return _style(fig, height=340)


def _sentiment_counts(df: pd.DataFrame) -> pd.DataFrame:
    order = ["Positive", "Neutral", "Negative"]
    counts = df["sentiment"].value_counts().reindex(order, fill_value=0)
    return counts.rename_axis("sentiment").reset_index(name="count")


def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=45, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", size=13, color="#111827"),
    )
    return fig
