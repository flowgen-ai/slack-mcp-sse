"""
Slack MCP Server in Python using FastMCP over SSE with FastAPI.
Dynamic multi-tenant support: tokens fetched from Postgres by team_id; channel listing via users.conversations with current_user_id.
"""
import os
import sys
import logging
from typing import Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI
import asyncpg
import httpx
from mcp.server.fastmcp import FastMCP

# — Load env & configure logging —
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slack_mcp")

# — Postgres connection URL —
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("Please set DATABASE_URL environment variable")
    sys.exit(1)

# — Instantiate FastMCP with no prefix —
mcp = FastMCP("SlackServer", path_prefix="")

# — Global DB pool placeholder —
db_pool: Optional[asyncpg.Pool] = None

# — FastAPI app & lifecycle —
app = FastAPI()
@app.on_event("startup")
async def startup_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    logger.info("Connected to Postgres at %s", DATABASE_URL)

@app.on_event("shutdown")
async def shutdown_db():
    await db_pool.close()
    logger.info("Postgres connection pool closed")

# — Helper to fetch bot_token for a given team_id —
async def get_bot_token(team_id: str) -> str:
    row = await db_pool.fetchrow(
        "SELECT bot_token FROM slack_bots WHERE team_id = $1", team_id
    )
    if not row:
        raise ValueError(f"No bot token found for team_id={team_id}")
    return row["bot_token"]

# — Slack service with dynamic token per team —
class SlackService:
    async def _slack_request(
        self,
        team_id: str,
        method: str,
        api: str,
        params: dict = None,
        json_payload: dict = None
    ) -> dict:
        token = await get_bot_token(team_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://slack.com/api/{api}"
        async with httpx.AsyncClient(headers=headers) as client:
            if method.upper() == "GET":
                resp = await client.get(url, params=params)
            else:
                resp = await client.post(url, json=json_payload)
            resp.raise_for_status()
            return resp.json()

    async def list_channels(self, team_id: str, user_id: str, limit: int = 100, cursor: str = None) -> dict:
        logger.info("list_channels called: team_id=%s, user_id=%s, limit=%s, cursor=%s", team_id, user_id, limit, cursor)
        # List both public and private channels for user
        params = {"user": user_id, "types": "public_channel,private_channel", "limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor
        return await self._slack_request(team_id, "GET", "users.conversations", params=params)

    async def post_message(self, team_id: str, channel_id: str, text: str) -> dict:
        logger.info("post_message called: team_id=%s, channel_id=%s", team_id, channel_id)
        return await self._slack_request(
            team_id, "POST", "chat.postMessage", json_payload={"channel": channel_id, "text": text}
        )

    async def post_reply(self, team_id: str, channel_id: str, thread_ts: str, text: str) -> dict:
        logger.info("post_reply called: team_id=%s, channel_id=%s, thread_ts=%s", team_id, channel_id, thread_ts)
        return await self._slack_request(
            team_id, "POST", "chat.postMessage", json_payload={"channel": channel_id, "thread_ts": thread_ts, "text": text}
        )

    async def add_reaction(self, team_id: str, channel_id: str, timestamp: str, reaction: str) -> dict:
        logger.info("add_reaction called: team_id=%s, channel_id=%s, timestamp=%s, reaction=%s", team_id, channel_id, timestamp, reaction)
        return await self._slack_request(
            team_id, "POST", "reactions.add", json_payload={"channel": channel_id, "timestamp": timestamp, "name": reaction}
        )

    async def get_channel_history(self, team_id: str, channel_id: str, limit: int = 10) -> dict:
        logger.info("get_channel_history called: team_id=%s, channel_id=%s, limit=%s", team_id, channel_id, limit)
        return await self._slack_request(
            team_id, "GET", "conversations.history", params={"channel": channel_id, "limit": limit}
        )

    async def get_thread_replies(self, team_id: str, channel_id: str, thread_ts: str) -> dict:
        logger.info("get_thread_replies called: team_id=%s, channel_id=%s, thread_ts=%s", team_id, channel_id, thread_ts)
        return await self._slack_request(
            team_id, "GET", "conversations.replies", params={"channel": channel_id, "ts": thread_ts}
        )

    async def get_users(self, team_id: str, limit: int = 100, cursor: str = None) -> dict:
        logger.info("get_users called: team_id=%s, limit=%s, cursor=%s", team_id, limit, cursor)
        params = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor
        return await self._slack_request(team_id, "GET", "users.list", params=params)

    async def get_user_profile(self, team_id: str, user_id: str) -> dict:
        logger.info("get_user_profile called: team_id=%s, user_id=%s", team_id, user_id)
        return await self._slack_request(
            team_id, "GET", "users.profile.get", params={"user": user_id, "include_labels": "true"}
        )

# — SlackService instance —
service = SlackService()

# — Tool definitions —
@mcp.tool(name="slack_list_channels", description="List channels for a user in a workspace")
async def slack_list_channels(team_id: str, current_user_id: str, limit: int = 100, cursor: Optional[str] = None) -> dict:
    return await service.list_channels(team_id, current_user_id, limit, cursor)

@mcp.tool(name="slack_post_message", description="Post a message to a channel")
async def slack_post_message(team_id: str, channel_id: str, text: str) -> dict:
    return await service.post_message(team_id, channel_id, text)

@mcp.tool(name="slack_reply_to_thread", description="Reply in a thread")
async def slack_reply_to_thread(team_id: str, channel_id: str, thread_ts: str, text: str) -> dict:
    return await service.post_reply(team_id, channel_id, thread_ts, text)

@mcp.tool(name="slack_add_reaction", description="Add reaction to a message")
async def slack_add_reaction(team_id: str, channel_id: str, timestamp: str, reaction: str) -> dict:
    return await service.add_reaction(team_id, channel_id, timestamp, reaction)

@mcp.tool(name="slack_get_channel_history", description="Get recent channel messages")
async def slack_get_channel_history(team_id: str, channel_id: str, limit: int = 10) -> dict:
    return await service.get_channel_history(team_id, channel_id, limit)

@mcp.tool(name="slack_get_thread_replies", description="Get thread replies")
async def slack_get_thread_replies(team_id: str, channel_id: str, thread_ts: str) -> dict:
    return await service.get_thread_replies(team_id, channel_id, thread_ts)

@mcp.tool(name="slack_get_users", description="List users in a workspace")
async def slack_get_users(team_id: str, limit: int = 100, cursor: Optional[str] = None) -> dict:
    return await service.get_users(team_id, limit, cursor)

@mcp.tool(name="slack_get_user_profile", description="Get user profile details")
async def slack_get_user_profile(team_id: str, user_id: str) -> dict:
    return await service.get_user_profile(team_id, user_id)

# — FastAPI mounting MCP SSE —
app = FastAPI()
app.mount("/", mcp.sse_app())

# — Run via Uvicorn —
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Slack MCP SSE server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
