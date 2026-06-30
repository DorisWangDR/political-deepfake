# Political Deepfake Atlas

An interactive Streamlit dashboard for exploring political deepfake and cheapfake incidents across platforms, targets, narratives, harms, and engagement signals.

**Live demo:** https://political-deepfake-demo.streamlit.app/

<img width="1903" height="809" alt="image" src="https://github.com/user-attachments/assets/3cc85426-e0a5-41ee-a581-bbc6bb0ef0ac" />

## Overview

Political Deepfake Atlas turns a manually coded incident database into an exploratory data visualization tool. The app is designed to help users move beyond individual examples and examine broader patterns in how political synthetic media circulates online.

The dashboard supports questions such as:

- Which political figures or groups are most frequently targeted?
- How do incidents vary across media formats, platforms, and time?
- Which communication goals and harm narratives appear most often?
- Which incidents receive the highest engagement?
- How do deepfakes, cheapfakes, uncertain cases, and real-content cases compare?

## Dataset

The project uses an exported version of the Political Deepfakes Incidents Database, introduced by Northwestern University's Center for Advancing Safety of Machine Intelligence.

- Dataset context: https://casmi.northwestern.edu/news/articles/2024/tracking-political-deepfakes-new-database-aims-to-inform-inspire-policy-solutions.html
- Local data file: `Database.csv`
- Current demo dataset size: 2,790 incidents and 184 coded fields

The dataset includes incident URLs, posting dates, media formats, content classifications, targets, sharers, engagement metrics, verification signals, communication goals, and coded harm or narrative categories.

## Features

- Interactive filters for year range, content classification, media format, communication goal, and platform
- Summary metrics for total incidents, deepfake and cheapfake shares, verification uncertainty, and watermark presence
- Timeline visualization of incidents by month and content type
- Target and platform ranking charts
- Log-scale engagement scatterplot comparing views, likes, and shares
- Narrative and harm visualizations based on multi-label coded fields
- Incident explorer for inspecting high-engagement individual cases

## Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- PyArrow

## Run Locally

Clone the repository, install dependencies, and start the Streamlit app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app expects `Database.csv` to be in the same folder as `app.py`.

## Project Structure

```text
.
├── app.py
├── Database.csv
├── requirements.txt
└── README.md
```

## Notes

This project was originally developed as a course demo and later refined as a portfolio project. The focus is on data cleaning, exploratory visualization, interaction design, and communicating social media research through an accessible web interface.

