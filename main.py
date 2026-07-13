import uvicorn
from src.app.factory import create_app
from src.context import build_context

if __name__ == "__main__":
    ctx = build_context()
    app = create_app(ctx)
    uvicorn.run(app)
