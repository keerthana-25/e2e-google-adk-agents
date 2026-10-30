"""FastAPI backend for the GenAI Sports agent.

POST /chat  {"message": "...", "session_id": "optional"}
  Header: Authorization: Bearer <Google ID token>   (required when GOOGLE_CLIENT_ID is set)

The signed-in user's email is taken from the verified ID token and bound into the tools,
so a user can only see / change their own shopping list and orders.
If GOOGLE_CLIENT_ID is not set (local dev), DEMO_USER_EMAIL is used instead.
"""

import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from google.auth.transport import requests as google_requests
from google.genai import types
from google.oauth2 import id_token
from pydantic import BaseModel

from sports_shop_agent.agent import build_agent

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("shop-server")

APP_NAME = "genai_sports"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
DEMO_USER_EMAIL = os.getenv("DEMO_USER_EMAIL", "alex@example.com")

# One shared session service so conversations keep their history between requests.
# Set SESSION_DB_URL (e.g. postgresql+asyncpg://...) to persist sessions in a database.
_db_url = os.getenv("SESSION_DB_URL")
session_service = DatabaseSessionService(db_url=_db_url) if _db_url else InMemorySessionService()

app = FastAPI(title="GenAI Sports Agent")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


def current_user_email(authorization: str | None) -> str:
    if not GOOGLE_CLIENT_ID:
        return DEMO_USER_EMAIL  # local dev mode
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    try:
        claims = id_token.verify_oauth2_token(
            authorization.removeprefix("Bearer "), google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    if not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="Email not verified")
    return claims["email"]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest, authorization: str | None = Header(default=None)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    email = current_user_email(authorization)
    session_id = req.session_id or str(uuid.uuid4())

    session = await session_service.get_session(app_name=APP_NAME, user_id=email, session_id=session_id)
    if session is None:
        await session_service.create_session(app_name=APP_NAME, user_id=email, session_id=session_id)

    runner = Runner(app_name=APP_NAME, agent=build_agent(email), session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=req.message)])

    async def stream():
        try:
            async for event in runner.run_async(user_id=email, session_id=session_id, new_message=content):
                if event.content and event.content.parts and event.is_final_response():
                    for part in event.content.parts:
                        if part.text:
                            yield part.text
        except Exception:
            log.exception("agent run failed")
            yield "\n[Sorry, something went wrong. Please try again.]"
        finally:
            await runner.close()  # closes the toolbox connection for this request

    return StreamingResponse(stream(), media_type="text/plain",
                             headers={"X-Session-Id": session_id})
