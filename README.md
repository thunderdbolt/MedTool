# Emerging Medical Device Explorer

A GitHub-ready Streamlit application for filtering, mapping, comparing, and reviewing emerging medical-device research.

## Features

- Loads the included Excel workbook from `data/`
- Automatically detects the workbook's real header row
- Excludes blank and placeholder product rows
- Search and multi-select filters
- Session-based Excel/CSV upload
- Product cards with optional images
- Interactive global map
- Side-by-side comparison
- Summary charts and filtered CSV download

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Sign in to Streamlit Community Cloud.
3. Select the repository, branch, and `app.py`.
4. Deploy.

## Add product images

Place images in the `images/` directory. You can either:

1. Add an `Image Path` column to the workbook, for example `images/dermalix.jpg`; or
2. Name each image using the normalized product name, for example:
   - `Asthana Stent` → `asthana_stent.jpg`
   - `CardiPulse™ PFA Catheter` → `cardipulse___pfa_catheter.jpg`

Using an explicit `Image Path` column is recommended.

## Recommended workbook columns

The existing workbook works as-is. For richer future releases, add:

- `Image Path`
- `Latitude`
- `Longitude`
- `Last Verified`
- `Source URL`
- `Evidence Level`

Uploaded files must contain at least `Product Name`, `Product Type`, and `Country of Origin`.
