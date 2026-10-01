import datetime
import uuid

import inngest
import inngest.fast_api

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()

# Temporary in-memory storage for reports
reports = {}


# -------------------------
# Inngest client
# -------------------------

inngest_client = inngest.Inngest(
    app_id="report-api",
)


# -------------------------
# Stage 1: say-hello
# -------------------------

@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep(
        "wait-5-seconds",
        datetime.timedelta(seconds=5),
    )

    return "Hello from the background!"


# -------------------------
# Stage 2: Request model
# -------------------------

class ReportRequest(BaseModel):
    topic: str


# -------------------------
# Stage 2: POST /reports
# -------------------------

@app.post("/reports", status_code=202)
async def create_report(request: ReportRequest):

    # Create a unique ID for this report
    report_id = str(uuid.uuid4())

    # Save the report as pending
    reports[report_id] = {
        "id": report_id,
        "topic": request.topic,
        "status": "pending",
    }

    # Send an event to Inngest
    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={
                "id": report_id,
                "topic": request.topic,
            },
        )
    )

    # Return immediately
    return {
        "id": report_id,
        "status": "pending",
    }


# -------------------------
# Stage 2: Background job
# -------------------------

@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
)
async def make_report(ctx: inngest.Context):

    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    # Step 1: pretend to do slow work
    await ctx.step.sleep(
        "do-the-slow-work",
        datetime.timedelta(seconds=8),
    )

    # Step 2: build and save the report
    async def build_report():
        result = f"Report generated about {topic}."

        reports[report_id] = {
            "id": report_id,
            "topic": topic,
            "status": "done",
            "result": result,
        }

        return result

    return await ctx.step.run(
        "build-report",
        build_report,
    )


# -------------------------
# Stage 2: GET /reports/{id}
# -------------------------

@app.get("/reports/{report_id}")
async def get_report(report_id: str):

    # Check whether the ID exists
    if report_id not in reports:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    # Return current report status
    return reports[report_id]


# -------------------------
# Inngest endpoint
# -------------------------

inngest.fast_api.serve(
    app,
    inngest_client,
    [
        say_hello,
        make_report,
    ],
)


# -------------------------
# Health check
# -------------------------

@app.get("/health")
def health():
    return {"status": "ok"}