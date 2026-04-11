from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from scheduler import scheduler, load_pending_reminders
from routers.events import router as events_router
from routers.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        scheduler.start()
        await load_pending_reminders()
    except Exception as e:
        import logging
        logging.warning(f"Startup warning (DB/scheduler): {e}")
    yield
    try:
        scheduler.shutdown()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(events_router)
