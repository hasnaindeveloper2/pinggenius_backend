from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.APScheduler import monitor_schedulers
from utils.scheduler import scheduler

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "PingGenius Agent API is running 🚀"}


@app.on_event("startup")
async def monitoring_schedulers():
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.create_task(monitor_schedulers())

    if not scheduler.running:
        scheduler.start()

    print("✅ Scheduler monitor started...")


# -------- Routers --------
from api.v1 import (
    analyze_email,
    outreach_email,
    save_contact,
    start_sequence,
    list_contacts,
    generate_sequence,
    hard_emails,
    stop_sequence,
    refine_hard_emails,
    list_all_email,
    gamail_scheduler,
    sequence_job_status,
)
app.include_router(analyze_email.router, prefix="/api/v1")
app.include_router(outreach_email.router, prefix="/api/v1")
app.include_router(save_contact.router, prefix="/api/v1")
app.include_router(list_contacts.router, prefix="/api/v1")
app.include_router(start_sequence.router, prefix="/api/v1")
app.include_router(stop_sequence.router, prefix="/api/v1")
app.include_router(sequence_job_status.router, prefix="/api/v1")
app.include_router(generate_sequence.router, prefix="/api/v1")
app.include_router(hard_emails.router, prefix="/api/v1")
app.include_router(refine_hard_emails.router, prefix="/api/v1")
app.include_router(list_all_email.router, prefix="/api/v1")
app.include_router(gamail_scheduler.router, prefix="/api/v1")
