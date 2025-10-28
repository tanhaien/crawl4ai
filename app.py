# Entry point for Streamlit Cloud
import os

# Disable watchdog-based file watcher to avoid inotify limits on Streamlit Cloud
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = os.environ.get(
    "STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none"
)

# Import the Streamlit app defined in app/main.py so that Streamlit executes it.
import app.main  # noqa: F401
