#!/usr/bin/env python3

import sys

import uvicorn

from app.main import app
from app.config import settings

if __name__ == "__main__":
    is_frozen = bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug and not is_frozen,
        use_colors=not is_frozen,
    )
