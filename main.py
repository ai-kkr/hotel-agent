import uvicorn
from src_v2.app.factory import create_app
from src_v2.context import build_context

if __name__ == "__main__":
    ctx = build_context()
    app = create_app(ctx)
    uvicorn.run(app)
