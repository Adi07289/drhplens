"""Mirror Streamlit-Cloud ``st.secrets`` into ``os.environ`` (import for side effect).

Streamlit Community Cloud exposes secrets via ``st.secrets``, but the agent/storage
layers read ``os.environ`` (fed locally by ``.env`` via python-dotenv). Importing this
module mirrors ``st.secrets`` into ``os.environ`` with ``setdefault`` (never overriding a
real env var), so the app runs unchanged on Streamlit Cloud, HF Spaces, or locally.

Import this at the TOP of any entry point / page that reads keys from ``os.environ``
(app.py and pages/ sub-scripts run as independent Streamlit scripts, so each needs it
before its own module-level env checks). No-op when there is no secrets file present.
"""
import os

try:
    import streamlit as st

    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    pass  # no secrets.toml (local dev uses .env); or no Streamlit runtime context
