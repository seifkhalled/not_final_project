import subprocess
from pathlib import Path

import modal

# ==============================
# CONFIG
# ==============================

LOCAL_DIR = Path(__file__).parent
REMOTE_DIR = "/root/app"
CHROMA_DB_REMOTE = "/root/chroma_db"

# ==============================
# VOLUME (persistent ChromaDB storage)
# ==============================

chroma_volume = modal.Volume.from_name("chroma-db", create_if_missing=True)

# ==============================
# IMAGE
# ==============================

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install(
        "chromadb>=0.4.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "sentence-transformers>=2.2.0",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "python-dotenv>=1.0.0",
        "groq>=0.4.0",
        "tavily-python>=0.5.0",
        "openai>=1.0.0",
    )
    .add_local_dir(
        LOCAL_DIR / "src",
        remote_path=f"{REMOTE_DIR}/src",
    )
    .add_local_dir(
        LOCAL_DIR / "ai",
        remote_path=f"{REMOTE_DIR}/ai",
    )
    .add_local_dir(
        LOCAL_DIR / "data",
        remote_path=f"{REMOTE_DIR}/data",
    )
    .add_local_file(
        LOCAL_DIR / "api_server.py",
        remote_path=f"{REMOTE_DIR}/api_server.py",
    )
)

# ==============================
# MODAL APP
# ==============================

app = modal.App("egypt-trip-planner", image=image)

# ==============================
# BUILD CHROMA DB (run once, persist to volume)
# ==============================

@app.function(volumes={CHROMA_DB_REMOTE: chroma_volume}, timeout=1800, gpu="T4")
def build_chroma_db():
    import os
    import sys

    sys.path.insert(0, REMOTE_DIR)

    os.environ["CHROMA_PATH"] = f"{CHROMA_DB_REMOTE}/travel_chroma_db"

    build_path = f"{REMOTE_DIR}/src/build_vector_db.py"
    with open(build_path, "r") as f:
        content = f.read()
    content = content.replace(
        'CHROMA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "chroma_db", "travel_chroma_db"))',
        f'CHROMA_PATH = "{CHROMA_DB_REMOTE}/travel_chroma_db"',
    )
    with open(build_path, "w") as f:
        f.write(content)

    from src import build_vector_db

    chroma_volume.commit()
    print("ChromaDB built and saved to volume!")

# ==============================
# FLASK API SERVER
# ==============================

@app.function(
    volumes={CHROMA_DB_REMOTE: chroma_volume},
    timeout=3600,
    secrets=[modal.Secret.from_name("egypt-trip-planner-secrets")],
)
@modal.concurrent(max_inputs=100)
@modal.web_server(8000, startup_timeout=120)
def run():
    import os
    import sys
    import threading

    sys.path.insert(0, REMOTE_DIR)

    # Point ChromaDB to the persistent volume
    os.environ["CHROMA_PATH"] = f"{CHROMA_DB_REMOTE}/travel_chroma_db"

    # Patch vector_search.py to use the volume path
    vector_search_path = f"{REMOTE_DIR}/src/vector_search.py"
    with open(vector_search_path, "r") as f:
        content = f.read()
    content = content.replace(
        'CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db", "travel_chroma_db")',
        f'CHROMA_PATH = "{CHROMA_DB_REMOTE}/travel_chroma_db"',
    )
    with open(vector_search_path, "w") as f:
        f.write(content)

    # Import the Flask app directly and run in a thread
    # This is the reliable way — subprocess shell=True with && fails silently in containers
    from api_server import app as flask_app

    def serve():
        flask_app.run(host="0.0.0.0", port=8000, debug=False)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
