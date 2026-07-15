from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = APP_DIR / "data" / "Emerging_Medical_Devices_Research.xlsx"
IMAGE_DIR = APP_DIR / "images"

st.set_page_config(
    page_title="Emerging Medical Device Explorer",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.7rem; padding-bottom: 3rem;}
      [data-testid="stMetric"] {background: rgba(120,120,120,.08); border: 1px solid rgba(120,120,120,.16); padding: 14px; border-radius: 14px;}
      .device-card {border: 1px solid rgba(120,120,120,.22); border-radius: 18px; padding: 18px; margin-bottom: 14px; background: rgba(120,120,120,.045);}
      .device-title {font-size: 1.25rem; font-weight: 750; margin-bottom: 5px;}
      .muted {opacity: .72;}
      .badge {display:inline-block; padding:4px 9px; margin:3px 4px 3px 0; border-radius:999px; background:rgba(50,120,190,.13); font-size:.78rem; font-weight:650;}
      .section-label {font-size:.78rem; font-weight:750; letter-spacing:.04em; text-transform:uppercase; opacity:.68; margin-top:8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

COLUMN_ALIASES = {
    "manufacturer/ developer": "Manufacturer/Developer",
    "manufacturer/developer": "Manufacturer/Developer",
    "u.s status": "U.S. Status",
    "u.s. status": "U.S. Status",
    "europe status": "Europe Status",
    "middle east status": "Middle East Status",
    "commercial status": "Commercial Status",
    "product type": "Product Type",
    "country of origin": "Country of Origin",
    "medical field": "Medical Field",
    "hospital need": "Hospital Need",
    "material used": "Material Used",
    "market potential": "Market Potential",
    "disadvantages/limitations": "Disadvantages/Limitations",
}

REQUIRED_COLUMNS = ["Product Name", "Product Type", "Country of Origin"]
TEXT_COLUMNS = [
    "Product Name", "Product Type", "Country of Origin", "Website",
    "Manufacturer/Developer", "Medical Field", "Hospital Need", "Innovation",
    "Material Used", "Advantages", "Disadvantages/Limitations", "U.S. Status",
    "Europe Status", "Middle East Status", "Commercial Status", "Market Potential",
    "Recommendation", "Image Path",
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return " ".join(text.split())


def split_bullets(value: object) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    parts = [p.strip(" •-\t") for p in text.replace("\n", " • ").split("•")]
    return [p for p in parts if p and p not in {"...", "[…]", "[ ... ]"}]


def first_nonempty(items: Iterable[str], fallback: str = "Not specified") -> str:
    return next((item for item in items if item), fallback)


def normalize_status(value: object) -> str:
    text = clean_text(value).lower()
    if not text:
        return "Not stated"
    negative = ("no public", "not confirmed", "not identified", "pending", "awaiting", "underway")
    if "approved" in text or "clearance" in text or "cleared" in text or "certification reported" in text or "ce certified" in text:
        if any(term in text for term in negative):
            return "Unconfirmed / pending"
        return "Approved / certified"
    if "commercial" in text or "available" in text or "marketed" in text or "sales" in text:
        if any(term in text for term in negative):
            return "Limited / unconfirmed"
        return "Commercially available"
    if "development" in text or "early-stage" in text or "pre-commercial" in text or "planned" in text:
        return "Under development"
    if any(term in text for term in negative):
        return "Unconfirmed / pending"
    return "Other"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = clean_text(col).lower()
        renamed[col] = COLUMN_ALIASES.get(key, clean_text(col))
    df = df.rename(columns=renamed)
    for col in TEXT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].map(clean_text)
    return df


@st.cache_data(show_spinner=False)
def load_default_data(path: str) -> pd.DataFrame:
    return read_data(Path(path))


def detect_excel_header(source) -> int:
    preview = pd.read_excel(source, header=None, nrows=12)
    for idx, row in preview.iterrows():
        values = {clean_text(v).lower() for v in row.tolist()}
        if "product name" in values and ("country of origin" in values or "product type" in values):
            return int(idx)
    return 0


def read_data(source) -> pd.DataFrame:
    name = getattr(source, "name", str(source)).lower()
    if name.endswith(".csv"):
        df = pd.read_csv(source)
    else:
        header_row = detect_excel_header(source)
        if hasattr(source, "seek"):
            source.seek(0)
        df = pd.read_excel(source, header=header_row)
    df = normalize_columns(df)
    df = df[df["Product Name"].str.len() > 0].copy()
    placeholder = df["Product Name"].str.fullmatch(r"\[?\s*\.{2,}\s*\]?", case=False, na=False)
    df = df[~placeholder].copy()
    df["US Category"] = df["U.S. Status"].map(normalize_status)
    df["Europe Category"] = df["Europe Status"].map(normalize_status)
    df["Middle East Category"] = df["Middle East Status"].map(normalize_status)
    df["Commercial Category"] = df["Commercial Status"].map(normalize_status)
    df["Primary Medical Field"] = df["Medical Field"].map(lambda x: first_nonempty(split_bullets(x)))
    return df.reset_index(drop=True)


def validate_data(df: pd.DataFrame) -> list[str]:
    return [col for col in REQUIRED_COLUMNS if col not in df.columns or df[col].eq("").all()]


def options_from_bullets(series: pd.Series) -> list[str]:
    values = set()
    for value in series:
        values.update(split_bullets(value))
    return sorted(values)


def contains_any(value: str, selected: list[str]) -> bool:
    if not selected:
        return True
    value_lower = value.lower()
    return any(item.lower() in value_lower for item in selected)


def website_url(value: str) -> str | None:
    candidate = first_nonempty(split_bullets(value), "")
    if not candidate or "no dedicated" in candidate.lower():
        return None
    return candidate if candidate.startswith(("http://", "https://")) else f"https://{candidate.strip()}"


def resolve_image(row: pd.Series) -> Path | None:
    candidates = []
    if row.get("Image Path"):
        candidates.append(APP_DIR / row["Image Path"])
        candidates.append(IMAGE_DIR / Path(row["Image Path"]).name)
    slug = "".join(c.lower() if c.isalnum() else "_" for c in row["Product Name"]).strip("_")
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        candidates.append(IMAGE_DIR / f"{slug}{ext}")
    return next((path for path in candidates if path.exists()), None)


st.title("Emerging Medical Device Explorer")
st.caption("Explore, compare, map, and evaluate emerging medical technologies from a GitHub-hosted research dataset.")

with st.sidebar:
    st.header("Data source")
    upload = st.file_uploader("Upload Excel or CSV", type=["xlsx", "xls", "csv"], help="The uploaded file is used only for this browser session.")
    try:
        data = read_data(upload) if upload else load_default_data(str(DEFAULT_DATA))
    except Exception as exc:
        st.error(f"Could not read the data file: {exc}")
        st.stop()

    missing = validate_data(data)
    if missing:
        st.error("Missing required columns: " + ", ".join(missing))
        st.stop()

    st.success(f"{len(data)} valid products loaded")
    st.divider()
    st.header("Filters")
    search = st.text_input("Search", placeholder="Product, material, innovation…")
    countries = st.multiselect("Country", sorted(data["Country of Origin"].dropna().unique()))
    product_types = st.multiselect("Product type", options_from_bullets(data["Product Type"]))
    fields = st.multiselect("Medical field", options_from_bullets(data["Medical Field"]))
    commercial = st.multiselect("Commercial status", sorted(data["Commercial Category"].unique()))
    us_status = st.multiselect("U.S. status", sorted(data["US Category"].unique()))
    eu_status = st.multiselect("Europe status", sorted(data["Europe Category"].unique()))
    me_status = st.multiselect("Middle East status", sorted(data["Middle East Category"].unique()))

filtered = data.copy()
if search:
    searchable_cols = [c for c in TEXT_COLUMNS if c in filtered.columns]
    mask = filtered[searchable_cols].apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
    filtered = filtered[mask]
if countries:
    filtered = filtered[filtered["Country of Origin"].isin(countries)]
if product_types:
    filtered = filtered[filtered["Product Type"].map(lambda x: contains_any(x, product_types))]
if fields:
    filtered = filtered[filtered["Medical Field"].map(lambda x: contains_any(x, fields))]
if commercial:
    filtered = filtered[filtered["Commercial Category"].isin(commercial)]
if us_status:
    filtered = filtered[filtered["US Category"].isin(us_status)]
if eu_status:
    filtered = filtered[filtered["Europe Category"].isin(eu_status)]
if me_status:
    filtered = filtered[filtered["Middle East Category"].isin(me_status)]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Products", len(filtered))
m2.metric("Countries", filtered["Country of Origin"].nunique())
m3.metric("Medical fields", filtered["Primary Medical Field"].nunique())
m4.metric("Commercially available", int((filtered["Commercial Category"] == "Commercially available").sum()))

explore_tab, map_tab, compare_tab, insights_tab, data_tab = st.tabs(["Explore", "Map", "Compare", "Insights", "Data"])

with explore_tab:
    if filtered.empty:
        st.info("No products match the current filters.")
    else:
        sort_choice = st.selectbox("Sort products", ["Product name", "Country", "Commercial status"], label_visibility="collapsed")
        sort_map = {"Product name": "Product Name", "Country": "Country of Origin", "Commercial status": "Commercial Category"}
        for _, row in filtered.sort_values(sort_map[sort_choice]).iterrows():
            with st.container():
                st.markdown('<div class="device-card">', unsafe_allow_html=True)
                image_col, info_col = st.columns([1, 3])
                image_path = resolve_image(row)
                with image_col:
                    if image_path:
                        st.image(str(image_path), use_container_width=True)
                    else:
                        st.markdown("### 🩺")
                        st.caption("Add a matching image to `/images` or provide an `Image Path` column.")
                with info_col:
                    st.markdown(f'<div class="device-title">{row["Product Name"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<span class="muted">{row["Country of Origin"]} · {first_nonempty(split_bullets(row["Product Type"]))}</span>', unsafe_allow_html=True)
                    badges = [row["Commercial Category"], row["US Category"], row["Europe Category"]]
                    st.markdown("".join(f'<span class="badge">{b}</span>' for b in badges), unsafe_allow_html=True)
                    st.markdown('<div class="section-label">Innovation</div>', unsafe_allow_html=True)
                    st.write(first_nonempty(split_bullets(row["Innovation"])))
                    url = website_url(row["Website"])
                    if url:
                        st.link_button("Product / manufacturer website", url)
                with st.expander("View full research profile"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Medical field**")
                        st.write(row["Medical Field"] or "Not stated")
                        st.markdown("**Hospital need**")
                        st.write(row["Hospital Need"] or "Not stated")
                        st.markdown("**Materials**")
                        st.write(row["Material Used"] or "Not stated")
                        st.markdown("**Advantages**")
                        st.write(row["Advantages"] or "Not stated")
                    with c2:
                        st.markdown("**Limitations**")
                        st.write(row["Disadvantages/Limitations"] or "Not stated")
                        st.markdown("**Commercial status**")
                        st.write(row["Commercial Status"] or "Not stated")
                        st.markdown("**Market potential**")
                        st.write(row["Market Potential"] or "Not stated")
                        st.markdown("**Recommendation**")
                        st.write(row["Recommendation"] or "Not stated")
                    st.markdown("**Regional regulatory status**")
                    st.write({"United States": row["U.S. Status"], "Europe": row["Europe Status"], "Middle East": row["Middle East Status"]})
                st.markdown('</div>', unsafe_allow_html=True)

with map_tab:
    st.subheader("Product origins")
    st.caption("Marker size reflects the number of matching products from each country. Use the filters to update the map.")
    if filtered.empty:
        st.info("No locations to map.")
    else:
        map_df = filtered.groupby("Country of Origin", as_index=False).agg(
            Products=("Product Name", "count"),
            Product_names=("Product Name", lambda s: "<br>".join(s)),
        )
        fig = px.scatter_geo(
            map_df,
            locations="Country of Origin",
            locationmode="country names",
            size="Products",
            hover_name="Country of Origin",
            hover_data={"Products": True, "Product_names": True},
            projection="natural earth",
            title="Global distribution of emerging medical devices",
        )
        fig.update_layout(height=620, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(map_df.rename(columns={"Product_names": "Products represented"}), use_container_width=True, hide_index=True)

with compare_tab:
    st.subheader("Compare products")
    choices = filtered["Product Name"].tolist()
    selected = st.multiselect("Choose up to four products", choices, max_selections=4)
    if not selected:
        st.info("Select products to create a side-by-side comparison.")
    else:
        compare_cols = ["Product Name", "Product Type", "Country of Origin", "Medical Field", "Innovation", "Material Used", "Advantages", "Disadvantages/Limitations", "Commercial Category", "US Category", "Europe Category", "Middle East Category", "Recommendation"]
        comparison = filtered[filtered["Product Name"].isin(selected)][compare_cols].set_index("Product Name").T
        st.dataframe(comparison, use_container_width=True)

with insights_tab:
    st.subheader("Dataset insights")
    if filtered.empty:
        st.info("No records available for charts.")
    else:
        country_counts = filtered["Country of Origin"].value_counts().rename_axis("Country").reset_index(name="Products")
        fig_country = px.bar(country_counts, x="Country", y="Products", title="Products by country")
        st.plotly_chart(fig_country, use_container_width=True)
        status_counts = filtered["Commercial Category"].value_counts().rename_axis("Status").reset_index(name="Products")
        fig_status = px.pie(status_counts, names="Status", values="Products", hole=.48, title="Commercial readiness")
        st.plotly_chart(fig_status, use_container_width=True)
        field_counts = filtered["Primary Medical Field"].value_counts().head(12).rename_axis("Medical field").reset_index(name="Products")
        fig_field = px.bar(field_counts, x="Products", y="Medical field", orientation="h", title="Leading medical fields")
        st.plotly_chart(fig_field, use_container_width=True)

with data_tab:
    st.subheader("Filtered research data")
    display_cols = [c for c in ["Product Name", "Product Type", "Country of Origin", "Medical Field", "Commercial Category", "US Category", "Europe Category", "Middle East Category", "Website"] if c in filtered.columns]
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data as CSV", csv, "filtered_medical_devices.csv", "text/csv")

st.divider()
st.caption("Research support tool only. Regulatory and commercial information should be independently verified before procurement or clinical decisions.")
