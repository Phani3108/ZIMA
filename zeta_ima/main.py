"""
Entry point for the Zeta IMA server.

Starts the FastAPI app (which includes the Teams bot webhook at POST /api/messages).

Usage:
    python -m zeta_ima.main
    # or
    uvicorn zeta_ima.api.app:app --reload --port 8000
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "zeta_ima.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
