import datetime
import inngest
import inngest.fast_api

from fastapi import FastAPI


app = FastAPI()


# Create Inngest client
inngest_client = inngest.Inngest(
    app_id="report-api",
)


# Create background function
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


# Serve Inngest functions
inngest.fast_api.serve(
    app,
    inngest_client,
    [say_hello],
)


@app.get("/health")
def health():
    return {"status": "ok"}