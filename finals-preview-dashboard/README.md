# 2026 NBA Finals: Knicks vs. Spurs Preview Platform

This is a working Streamlit MVP for a Knicks vs. Spurs NBA Finals scouting dashboard.

## Important data note

This first version uses static sample/proxy data so the app runs immediately. The live NBA.com/stats, Basketball-Reference, and PBPStats ingestion layer should be added in Batch 2.

## Local setup

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository named `finals-preview-dashboard`.
2. Upload all files in this folder.
3. Go to Streamlit Community Cloud.
4. Choose **New app**.
5. Connect the GitHub repository.
6. Set the main file path to `app.py`.
7. Click **Deploy**.
8. Streamlit will generate a public link.
