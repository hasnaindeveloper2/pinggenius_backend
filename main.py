from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "PingGenius Agent API is running 🚀"}


# -------- Routers --------
app.include_router(analyze_email.router, prefix="/api/v1")
app.include_router(outreach_email.router, prefix="/api/v1")
app.include_router(save_contact.router, prefix="/api/v1")
app.include_router(start_sequence.router, prefix="/api/v1")
app.include_router(list_contacts.router, prefix="/api/v1")
app.include_router(stop_sequence.router, prefix="/api/v1")
app.include_router(generate_sequence.router, prefix="/api/v1")
app.include_router(hard_emails.router, prefix="/api/v1")
app.include_router(refine_hard_emails.router, prefix="/api/v1")
app.include_router(list_all_email.router, prefix="/api/v1")
app.include_router(gamail_scheduler.router, prefix="/api/v1")
