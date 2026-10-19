"""Sugar Cosmetics Instagram Performance Dashboard.
Run:  pip install -r requirements.txt  then  streamlit run app.py
Put sugar_cosmetics_instagram_data.xlsx next to this file, or upload it in the sidebar.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Sugar Cosmetics Instagram", page_icon="💄", layout="wide")
FILE = "sugar_cosmetics_instagram_data.xlsx"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@st.cache_data(show_spinner="Loading data…")
def load(src):
    df = pd.read_excel(src)
    d = df["Post Date"]
    df["Date"] = pd.to_datetime(d, unit="D", origin="1899-12-30") if np.issubdtype(d.dtype, np.number) else pd.to_datetime(d)
    df["Total Engagement"] = df[["Likes", "Comments", "Shares", "Saves"]].sum(axis=1)
    df["Engagement Rate"] = np.where(df.Reach > 0, df["Total Engagement"] / df.Reach * 100, np.nan)
    df["Profile Visit Rate"] = np.where(df.Reach > 0, df["Profile Visits"] / df.Reach * 100, np.nan)
    df["Follow Conversion"] = np.where(df["Profile Visits"] > 0, df.Follows / df["Profile Visits"] * 100, np.nan)
    df["Day of Week"] = pd.Categorical(df.Date.dt.day_name(), DAYS, ordered=True)
    df["Month"] = df.Date.dt.to_period("M").astype(str)
    return df


up = st.sidebar.file_uploader("Upload Excel file (optional)", type="xlsx")
try:
    df = load(up if up else FILE)
except FileNotFoundError:
    st.error(f"Place `{FILE}` next to app.py or upload it in the sidebar.")
    st.stop()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
dmin, dmax = df.Date.min().date(), df.Date.max().date()
dr = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
f = {}
for col in ["Post Type", "Campaign Type", "Engagement Source", "Audience Emotion"]:
    f[col] = st.sidebar.multiselect(col, sorted(df[col].unique()), default=sorted(df[col].unique()))
m = df[list(f)].apply(lambda s: s.isin(f[s.name])).all(axis=1)
if len(dr) == 2:
    m &= df.Date.dt.date.between(*dr)
d = df[m]
if d.empty:
    st.warning("No records match the filters.")
    st.stop()

st.title("💄 Sugar Cosmetics: Instagram Performance")
st.caption("Engagement = likes + comments + shares + saves. Engagement rate = engagement ÷ reach × 100, averaged per record. "
           "Summed reach counts the same account more than once, so it is not unique people reached.")

# ---------- 1. KPIs ----------
st.subheader("1 · KPI overview")
k = st.columns(5)
k[0].metric("Records", f"{len(d):,}")
k[1].metric("Impressions", f"{d.Impressions.sum()/1e6:,.1f}M")
k[2].metric("Summed reach", f"{d.Reach.sum()/1e6:,.1f}M")
k[3].metric("Likes", f"{d.Likes.sum()/1e6:,.1f}M")
k[4].metric("Comments", f"{d.Comments.sum()/1e6:,.2f}M")
k = st.columns(5)
k[0].metric("Total engagement", f"{d['Total Engagement'].sum()/1e6:,.1f}M")
k[1].metric("Avg engagement rate", f"{d['Engagement Rate'].mean():.2f}%")
k[2].metric("Profile visit rate", f"{d['Profile Visits'].sum()/d.Reach.sum()*100:.2f}%")
k[3].metric("Follow per visit", f"{d.Follows.sum()/d['Profile Visits'].sum()*100:.1f}%")
k[4].metric("Reach ÷ impressions", f"{d.Reach.sum()/d.Impressions.sum()*100:.1f}%")

# ---------- 2. Monthly trend ----------
st.subheader("2 · Monthly posting trend")
mt = d.groupby("Month").agg(Records=("Month", "size"), Rate=("Engagement Rate", "mean")).reset_index()
c1, c2 = st.columns(2)
c1.plotly_chart(px.bar(mt, x="Month", y="Records", title="Records per month (Apr 2024 and Apr 2025 are partial)"), use_container_width=True)
c2.plotly_chart(px.line(mt, x="Month", y="Rate", markers=True, title="Avg engagement rate (%)"), use_container_width=True)

# ---------- 3 & 4. Top 10 ----------
cols = ["Date", "Post Type", "Campaign Type", "Likes", "Comments", "Shares", "Saves", "Reach", "Engagement Rate"]
st.subheader("3 · Top 10 records by likes")
st.dataframe(d.nlargest(10, "Likes")[cols].round(2), hide_index=True, use_container_width=True)
st.subheader("4 · Top 10 records by engagement rate")
st.dataframe(d.nlargest(10, "Engagement Rate")[cols].round(2), hide_index=True, use_container_width=True)

# ---------- 5. Post type ----------
st.subheader("5 · Post type performance")
pt = d.groupby("Post Type").agg(Records=("Likes", "size"), Likes=("Likes", "mean"), Comments=("Comments", "mean"),
                                Shares=("Shares", "mean"), Saves=("Saves", "mean"), Rate=("Engagement Rate", "mean")).reset_index()
c1, c2 = st.columns(2)
c1.plotly_chart(px.bar(pt, x="Post Type", y="Rate", text=pt.Rate.round(2), title="Avg engagement rate (%)"), use_container_width=True)
c2.plotly_chart(px.bar(pt.melt("Post Type", ["Likes", "Comments", "Shares", "Saves"]), x="Post Type", y="value",
                       color="variable", barmode="group", title="Average interactions per record"), use_container_width=True)
st.dataframe(pt.round(2), hide_index=True, use_container_width=True)

# ---------- 6. Day of week ----------
st.subheader("6 · Day of week")
dw = d.groupby("Day of Week", observed=True).agg(Records=("Likes", "size"), Rate=("Engagement Rate", "mean")).reset_index()
c1, c2 = st.columns(2)
c1.plotly_chart(px.bar(dw, x="Day of Week", y="Records", title="Posting frequency"), use_container_width=True)
c2.plotly_chart(px.bar(dw, x="Day of Week", y="Rate", text=dw.Rate.round(2), title="Avg engagement rate (%)"), use_container_width=True)

# ---------- 7. Funnel ----------
st.subheader("7 · Engagement funnel")
fn = go.Figure(go.Funnel(y=["Impressions", "Reach", "Interactions", "Profile visits", "Follows"],
                         x=[d.Impressions.sum(), d.Reach.sum(), d["Total Engagement"].sum(), d["Profile Visits"].sum(), d.Follows.sum()],
                         textinfo="value+percent previous"))
st.plotly_chart(fn, use_container_width=True)

# ---------- 8. Hashtags ----------
st.subheader("8 · Hashtag analysis")
d = d.assign(Tags=d.Hashtags.str.split(r",\s*"))
d["Rate vs peers"] = d["Engagement Rate"] - d.groupby(["Post Type", "Campaign Type"], observed=True)["Engagement Rate"].transform("mean")
rows = []
for h in sorted({t for ts in d.Tags for t in ts}):
    has = d.Tags.apply(lambda ts: h in ts)
    rows.append({"Hashtag": h, "Records": int(has.sum()), "Avg rate (%)": d.loc[has, "Engagement Rate"].mean(),
                 "Rate without (%)": d.loc[~has, "Engagement Rate"].mean(), "Adjusted Δ (pts)": d.loc[has, "Rate vs peers"].mean(),
                 "Avg reach": d.loc[has, "Reach"].mean(), "Avg likes": d.loc[has, "Likes"].mean()})
ht = pd.DataFrame(rows).round(2)
c1, c2 = st.columns([3, 2])
c1.dataframe(ht, hide_index=True, use_container_width=True)
c2.plotly_chart(px.bar(ht, x="Hashtag", y="Adjusted Δ (pts)", title="Adjusted gap vs same format and campaign"), use_container_width=True)
st.caption("Adjusted Δ compares each record with others of the same post type and campaign, so a hashtag is not credited for a strong format.")

# ---------- 9. Reach vs engagement ----------
st.subheader("9 · Reach without interaction")
s = d.sample(min(5000, len(d)), random_state=1)
st.plotly_chart(px.scatter(s, x="Reach", y="Engagement Rate", color="Post Type", opacity=0.4,
                           title="Reach vs engagement rate (sample of up to 5,000 records)"), use_container_width=True)
hi, lo = d.Reach >= d.Reach.quantile(.75), d["Engagement Rate"] <= d["Engagement Rate"].quantile(.25)
st.write(f"Correlation of reach and engagement rate: **{d.Reach.corr(d['Engagement Rate']):.2f}**. "
         f"Share of top-quartile-reach records that are also bottom-quartile for rate: **{(hi & lo).sum()/hi.sum()*100:.0f}%** "
         "(25% is what chance predicts).")

# ---------- 10. Recommendations ----------
st.subheader("10 · Strategic recommendations")
st.markdown("""
1. **Verify the data first.** Confirm what one row represents; 50,000 posts in a year is not plausible for a single account, and category averages are unusually uniform.
2. **Don't shift budget by format, weekday or hashtag yet.** Gaps are about 0.1 to 0.3 points and not statistically significant on the full file.
3. **Run controlled tests.** Same creative as Reel vs Image, same slot, matched audience.
4. **Work on the funnel.** About 3% of reach visits the profile and about 30% of visitors follow; profile CTAs are a clearer lever than format.
5. **Track saves and shares separately** as intent signals, and add post ID, post time and ad spend to the data.
""")
with st.expander("Data validation"):
    st.write({"rows": len(df), "columns": df.shape[1] - 9, "missing values": int(df.iloc[:, :14].isnull().sum().sum()),
              "duplicate rows": int(df.iloc[:, :14].duplicated().sum()), "reach > impressions": int((df.Reach > df.Impressions).sum()),
              "date range": f"{dmin} to {dmax}"})
