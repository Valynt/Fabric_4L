from fastapi import FastAPI
from app.routers.layer_delegation import router

def test_debug_included_router():
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    w = app.routes[-1]
    print("TYPE", type(w).__name__)
    print("ATTRS", [a for a in dir(w) if not a.startswith("__")])
    inner = getattr(w, "original_router", None)
    print("INNER_PATHS", sorted({r.path for r in inner.routes})[:6])
