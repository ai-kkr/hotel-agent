import uvicorn
from src.app.factory import create_app
from src.context import build_context

if __name__ == "__main__":
    ctx = build_context()
    app = create_app(ctx)
    # Внутренний порт приложения фиксирован (8000). Публикация на хост-портах настраивается
    # только в docker-compose (host:container mapping).
    uvicorn.run(app, host="0.0.0.0", port=8000)
