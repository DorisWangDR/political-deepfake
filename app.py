from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


DATA_PATH = Path(__file__).with_name("Database.csv")
DISPLAY_YEAR_FLOOR = 2016

PAGE_TITLE = "Political Deepfake Atlas"
SOURCE_URL = (
    "https://casmi.northwestern.edu/news/articles/2024/"
    "tracking-political-deepfakes-new-database-aims-to-inform-inspire-policy-solutions.html"
)

TYPE_COLORS = {
    "deepfake": "#d94f45",
    "cheapfake": "#f2a541",
    "unclear/unknown": "#7b8fa1",
    "real": "#3aa76d",
    "Unknown": "#9aa3ad",
}


def normalize_missing(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if not text:
        return pd.NA
    if text.lower() in {"nan", "none", "null"}:
        return pd.NA
    return text


def clean_label(value: object, fallback: str = "Unknown") -> str:
    value = normalize_missing(value)
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    text = text.replace("_", " ")
    return text[:1].upper() + text[1:] if text else fallback


def parse_number(value: object) -> float | None:
    value = normalize_missing(value)
    if pd.isna(value):
        return None

    text = str(value).strip().lower().replace(",", "")
    match = re.match(r"^([0-9]*\.?[0-9]+)\s*([kmb])?$", text)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2)
    if unit == "k":
        number *= 1_000
    elif unit == "m":
        number *= 1_000_000
    elif unit == "b":
        number *= 1_000_000_000
    return number


def compact_number(value: object) -> str:
    if value is None or pd.isna(value):
        return "Unknown"
    value = float(value)
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def extract_platform(url: object) -> str:
    url = normalize_missing(url)
    if pd.isna(url):
        return "Unknown"

    netloc = urlparse(str(url)).netloc.lower().replace("www.", "")
    if not netloc:
        return "Unknown"

    if netloc in {"x.com", "twitter.com", "mobile.twitter.com"}:
        return "X / Twitter"
    if "tiktok.com" in netloc:
        return "TikTok"
    if "instagram.com" in netloc:
        return "Instagram"
    if netloc in {"youtube.com", "youtu.be", "m.youtube.com"}:
        return "YouTube"
    if "facebook.com" in netloc:
        return "Facebook"
    if "reddit.com" in netloc:
        return "Reddit"
    if "bsky.app" in netloc:
        return "Bluesky"
    if "truthsocial.com" in netloc:
        return "Truth Social"
    return netloc


def split_values(series: pd.Series) -> pd.Series:
    values = (
        series.dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .str.strip()
        .replace("", pd.NA)
        .dropna()
    )
    return values.map(lambda item: clean_label(item))


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, dtype=str, encoding="utf-8-sig")
    df = df.map(normalize_missing)

    df["posted_date"] = pd.to_datetime(df["date_posted"], errors="coerce")
    df["posted_year"] = df["posted_date"].dt.year
    df["posted_month"] = df["posted_date"].dt.to_period("M").dt.to_timestamp()
    df["type_clean"] = df["type"].map(lambda item: clean_label(item))
    df["format_clean"] = df["format"].map(lambda item: clean_label(item))
    df["platform"] = df["url"].map(extract_platform)

    for metric in ["views", "likes", "shares", "comments"]:
        df[f"{metric}_num"] = df[metric].map(parse_number)

    df["engagement_total"] = df[
        ["views_num", "likes_num", "shares_num", "comments_num"]
    ].sum(axis=1, min_count=1)
    df["event_label"] = df.apply(make_event_label, axis=1)
    return df


def make_event_label(row: pd.Series) -> str:
    target = clean_label(row.get("target_one_name"), "Unknown target")
    platform = clean_label(row.get("platform"), "Unknown platform")
    date = row.get("posted_date")
    date_text = date.strftime("%Y-%m-%d") if pd.notna(date) else "No date"
    return f"{target} | {platform} | {date_text}"


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")

    valid_years = sorted(
        year
        for year in df["posted_year"].dropna().astype(int).unique()
        if year >= DISPLAY_YEAR_FLOOR
    )
    default_range = (
        max(min(valid_years), 2019),
        min(max(valid_years), 2026),
    )
    year_range = st.sidebar.slider(
        "Posted year",
        min_value=min(valid_years),
        max_value=max(valid_years),
        value=default_range,
    )

    selected_types = st.sidebar.multiselect(
        "Content classification",
        sorted(df["type_clean"].dropna().unique()),
        default=[item for item in ["Deepfake", "Cheapfake", "Unclear/unknown"] if item in set(df["type_clean"])],
    )
    selected_formats = st.sidebar.multiselect(
        "Media format",
        sorted(df["format_clean"].dropna().unique()),
        default=[item for item in ["Image", "Video", "Audio"] if item in set(df["format_clean"])],
    )

    goal_options = sorted(split_values(df["communication_goal"]).unique())
    selected_goals = st.sidebar.multiselect(
        "Communication goal",
        goal_options,
        default=[],
        help="Leave blank to include every coded goal.",
    )

    platforms = sorted(df["platform"].dropna().unique())
    selected_platforms = st.sidebar.multiselect(
        "Platform",
        platforms,
        default=[],
        help="Leave blank to include every platform.",
    )

    filtered = df[
        df["posted_year"].between(year_range[0], year_range[1], inclusive="both")
        | df["posted_year"].isna()
    ].copy()

    if selected_types:
        filtered = filtered[filtered["type_clean"].isin(selected_types)]
    if selected_formats:
        filtered = filtered[filtered["format_clean"].isin(selected_formats)]
    if selected_platforms:
        filtered = filtered[filtered["platform"].isin(selected_platforms)]
    if selected_goals:
        goal_mask = filtered["communication_goal"].fillna("").apply(
            lambda value: any(goal.lower().replace(" ", "_") in value.lower() for goal in selected_goals)
        )
        filtered = filtered[goal_mask]

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Data source: Political Deepfakes Incidents Database, exported as Database.csv."
    )
    return filtered


def metric_cards(df: pd.DataFrame) -> None:
    total = len(df)
    deepfake_share = share_of(df, "type", "deepfake")
    cheapfake_share = share_of(df, "type", "cheapfake")
    unknown_verification = share_of(df, "external_verification", "unknown")
    no_watermark = share_of(df, "watermark", "no")
    top_views = df["views_num"].max()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Incidents", f"{total:,}")
    c2.metric("Deepfake", f"{deepfake_share:.0%}")
    c3.metric("Cheapfake", f"{cheapfake_share:.0%}")
    c4.metric("Verification unknown", f"{unknown_verification:.0%}")
    c5.metric("No watermark", f"{no_watermark:.0%}", help=f"Top views: {compact_number(top_views)}")


def share_of(df: pd.DataFrame, column: str, value: str) -> float:
    if df.empty or column not in df:
        return 0.0
    return df[column].fillna("").astype(str).str.lower().eq(value).mean()


def time_trend_chart(df: pd.DataFrame) -> go.Figure:
    trend = (
        df.dropna(subset=["posted_month"])
        .groupby(["posted_month", "type_clean"], as_index=False)
        .size()
        .rename(columns={"size": "incidents"})
    )
    fig = px.area(
        trend,
        x="posted_month",
        y="incidents",
        color="type_clean",
        color_discrete_map=TYPE_COLORS,
        labels={"posted_month": "Posted month", "incidents": "Incidents", "type_clean": "Type"},
    )
    fig.update_layout(legend_title_text="", hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10))
    return fig


def target_chart(df: pd.DataFrame) -> go.Figure:
    targets = (
        df["target_one_name"]
        .map(lambda item: clean_label(item, "Unknown target"))
        .value_counts()
        .head(15)
        .sort_values()
        .rename_axis("target")
        .reset_index(name="incidents")
    )
    fig = px.bar(
        targets,
        x="incidents",
        y="target",
        orientation="h",
        color="incidents",
        color_continuous_scale=["#9bc8c2", "#234d5f"],
        labels={"target": "", "incidents": "Incidents"},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def platform_chart(df: pd.DataFrame) -> go.Figure:
    platforms = (
        df["platform"]
        .value_counts()
        .head(12)
        .sort_values()
        .rename_axis("platform")
        .reset_index(name="incidents")
    )
    fig = px.bar(
        platforms,
        x="incidents",
        y="platform",
        orientation="h",
        color="incidents",
        color_continuous_scale=["#f5c16c", "#7c3f20"],
        labels={"platform": "", "incidents": "Incidents"},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def influence_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df.dropna(subset=["views_num", "likes_num"]).copy()
    if plot_df.empty:
        return go.Figure().update_layout(title="No parsable engagement data")

    plot_df["target"] = plot_df["target_one_name"].map(lambda item: clean_label(item, "Unknown target"))
    plot_df["hover_summary"] = plot_df["summary_content"].fillna("No summary").astype(str).str.slice(0, 180)
    plot_df["bubble_size"] = plot_df["shares_num"].fillna(0).clip(lower=1)

    fig = px.scatter(
        plot_df,
        x="views_num",
        y="likes_num",
        size="bubble_size",
        color="type_clean",
        color_discrete_map=TYPE_COLORS,
        hover_name="event_label",
        hover_data={
            "target": True,
            "platform": True,
            "views_num": ":,.0f",
            "likes_num": ":,.0f",
            "shares_num": ":,.0f",
            "hover_summary": True,
            "bubble_size": False,
            "type_clean": False,
        },
        labels={"views_num": "Views", "likes_num": "Likes", "type_clean": "Type"},
    )
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=30, b=10))
    return fig


def multi_value_chart(df: pd.DataFrame, column: str, title: str, color_scale: list[str]) -> go.Figure:
    values = split_values(df[column]).value_counts().head(12).sort_values()
    chart_df = values.rename_axis(title).reset_index(name="incidents")
    fig = px.bar(
        chart_df,
        x="incidents",
        y=title,
        orientation="h",
        color="incidents",
        color_continuous_scale=color_scale,
        labels={title: "", "incidents": "Incidents"},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def narrative_heatmap(df: pd.DataFrame) -> go.Figure:
    goals = df[["incident_id", "communication_goal", "harm_evidence"]].copy()
    goals["goal"] = goals["communication_goal"].fillna("").str.split(",")
    goals["harm"] = goals["harm_evidence"].fillna("").str.split(",")
    exploded = goals.explode("goal").explode("harm")
    exploded["goal"] = exploded["goal"].map(lambda item: clean_label(item, "Unknown"))
    exploded["harm"] = exploded["harm"].map(lambda item: clean_label(item, "Unknown"))
    exploded = exploded[(exploded["goal"] != "Unknown") & (exploded["harm"] != "Unknown")]

    top_goals = exploded["goal"].value_counts().head(8).index
    top_harms = exploded["harm"].value_counts().head(8).index
    heat = exploded[exploded["goal"].isin(top_goals) & exploded["harm"].isin(top_harms)]
    heat = heat.groupby(["goal", "harm"], as_index=False).size().rename(columns={"size": "incidents"})

    fig = px.density_heatmap(
        heat,
        x="goal",
        y="harm",
        z="incidents",
        histfunc="sum",
        color_continuous_scale=["#f6efe5", "#d66b4d", "#531f2a"],
        labels={"goal": "Communication goal", "harm": "Harm evidence", "incidents": "Incidents"},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    return fig


def event_explorer(df: pd.DataFrame) -> None:
    st.subheader("Incident Explorer")
    if df.empty:
        st.info("No incidents match the current filters.")
        return

    sort_metric = st.selectbox("Rank incidents by", ["views_num", "likes_num", "shares_num", "comments_num", "engagement_total"], format_func=lambda x: x.replace("_num", "").replace("_", " ").title())
    ranked = df.sort_values(sort_metric, ascending=False, na_position="last").head(100).copy()
    selected_label = st.selectbox("Choose an incident", ranked["event_label"].tolist())
    row = ranked[ranked["event_label"] == selected_label].iloc[0]

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown(f"**Summary:** {row.get('summary_content') or 'No summary available.'}")
        st.markdown(f"**URL:** {row.get('url') or 'Unknown'}")
        st.markdown(f"**Target:** {clean_label(row.get('target_one_name'), 'Unknown target')} ({clean_label(row.get('target_one_sentiment'), 'Unknown sentiment')})")
        st.markdown(f"**Sharer:** {clean_label(row.get('sharer_name'), 'Unknown sharer')} | {clean_label(row.get('sharer_type'), 'Unknown type')}")
    with right:
        detail = pd.DataFrame(
            {
                "Field": [
                    "Posted date",
                    "Platform",
                    "Type",
                    "Format",
                    "External verification",
                    "Watermark",
                    "Views",
                    "Likes",
                    "Shares",
                    "Comments",
                ],
                "Value": [
                    row["posted_date"].strftime("%Y-%m-%d") if pd.notna(row["posted_date"]) else "Unknown",
                    clean_label(row.get("platform")),
                    clean_label(row.get("type")),
                    clean_label(row.get("format")),
                    clean_label(row.get("external_verification")),
                    clean_label(row.get("watermark")),
                    compact_number(row.get("views_num")),
                    compact_number(row.get("likes_num")),
                    compact_number(row.get("shares_num")),
                    compact_number(row.get("comments_num")),
                ],
            }
        )
        st.dataframe(detail, hide_index=True, use_container_width=True)


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
            max-width: 1320px;
        }
        div[data-testid="stMetric"] {
            background: #f7f4ef;
            border: 1px solid #e2ded6;
            border-radius: 8px;
            padding: 14px 16px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="PD", layout="wide")
    apply_theme()

    df = load_data()
    filtered = sidebar_filters(df)

    st.title(PAGE_TITLE)
    st.caption(
        "An interactive investigation desk for political deepfake incidents: targets, platforms, narratives, harms, and reach."
    )
    st.markdown(f"Dataset context: [Northwestern CASMI article]({SOURCE_URL})")

    metric_cards(filtered)

    st.divider()
    st.subheader("Timeline and Targets")
    chart_left, chart_right = st.columns([1.35, 1])
    with chart_left:
        st.plotly_chart(time_trend_chart(filtered), use_container_width=True)
    with chart_right:
        st.plotly_chart(target_chart(filtered), use_container_width=True)

    st.subheader("Reach and Platforms")
    reach_left, reach_right = st.columns([1.35, 1])
    with reach_left:
        st.plotly_chart(influence_chart(filtered), use_container_width=True)
    with reach_right:
        st.plotly_chart(platform_chart(filtered), use_container_width=True)

    st.subheader("Narratives and Harms")
    n1, n2, n3 = st.columns(3)
    with n1:
        st.plotly_chart(multi_value_chart(filtered, "communication_goal", "Communication goal", ["#dbe9e5", "#2f6f73"]), use_container_width=True)
    with n2:
        st.plotly_chart(multi_value_chart(filtered, "core_frame", "Core frame", ["#f1e1d2", "#9a5335"]), use_container_width=True)
    with n3:
        st.plotly_chart(multi_value_chart(filtered, "harm_evidence", "Harm evidence", ["#e5e1f2", "#59447a"]), use_container_width=True)

    st.plotly_chart(narrative_heatmap(filtered), use_container_width=True)

    st.divider()
    event_explorer(filtered)


if __name__ == "__main__":
    main()
