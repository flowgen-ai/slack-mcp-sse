#!/usr/bin/env python3
import os
import logging
import requests
import psycopg2
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP

# — Load env & configure logging —
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in your .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slack_mcp")


def fetch_bot_token(team_id: str) -> str:
    """
    Retrieve the Slack bot token for a given team_id from Postgres.
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT bot_token FROM slack_bots WHERE team_id = %s", (team_id,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"No bot_token found for team_id {team_id}")
            return row[0]
    finally:
        conn.close()


class SlackClient:
    def _get_headers(self, team_id: str) -> dict:
        token = fetch_bot_token(team_id)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get_user_conversations(
        self,
        team_id: str,
        current_user_id: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """
        List public and private channels the current_user is a member of.
        """
        headers = self._get_headers(team_id)
        params = {
            "user": current_user_id,
            "types": "public_channel,private_channel",
            "limit": min(limit, 200),
        }
        if cursor:
            params["cursor"] = cursor

        return requests.get(
            "https://slack.com/api/users.conversations",
            headers=headers,
            params=params,
        ).json()

    def post_message(self, team_id: str, channel_id: str, text: str) -> dict:
        headers = self._get_headers(team_id)
        return requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": channel_id, "text": text},
        ).json()

    def post_reply(
        self, team_id: str, channel_id: str, thread_ts: str, text: str
    ) -> dict:
        headers = self._get_headers(team_id)
        return requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": channel_id, "thread_ts": thread_ts, "text": text},
        ).json()

    def add_reaction(
        self, team_id: str, channel_id: str, timestamp: str, reaction: str
    ) -> dict:
        headers = self._get_headers(team_id)
        return requests.post(
            "https://slack.com/api/reactions.add",
            headers=headers,
            json={"channel": channel_id, "timestamp": timestamp, "name": reaction},
        ).json()

    def get_channel_history(
        self, team_id: str, channel_id: str, limit: int = 10
    ) -> dict:
        headers = self._get_headers(team_id)
        return requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params={"channel": channel_id, "limit": limit},
        ).json()

    def get_thread_replies(
        self, team_id: str, channel_id: str, thread_ts: str
    ) -> dict:
        headers = self._get_headers(team_id)
        return requests.get(
            "https://slack.com/api/conversations.replies",
            headers=headers,
            params={"channel": channel_id, "ts": thread_ts},
        ).json()

    def get_users(
        self, team_id: str, limit: int = 100, cursor: Optional[str] = None
    ) -> dict:
        headers = self._get_headers(team_id)
        params = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor
        return requests.get(
            "https://slack.com/api/users.list",
            headers=headers,
            params=params,
        ).json()

    def get_user_profile(self, team_id: str, user_id: str) -> dict:
        headers = self._get_headers(team_id)
        return requests.get(
            "https://slack.com/api/users.profile.get",
            headers=headers,
            params={"user": user_id, "include_labels": True},
        ).json()


# — Instantiate FastMCP and Slack client —
mcp = FastMCP("SlackMCPServer", path_prefix="")
slack = SlackClient()

# — Tools definitions — #
@mcp.tool(
    name="slack_list_channels",
    description="List all public and private channels for a user",
)
def slack_list_channels(
    team_id: str, current_user_id: str, limit: int = 100, cursor: Optional[str] = None
):
    logger.info(
        "slack_list_channels called team=%s user=%s limit=%s cursor=%s",
        team_id,
        current_user_id,
        limit,
        cursor,
    )
    return slack.get_user_conversations(team_id, current_user_id, limit, cursor)


@mcp.tool(
    name="slack_get_channel_history",
    description="Get recent messages from a channel if the user has access",
)
def slack_get_channel_history(
    team_id: str, current_user_id: str, channel_id: str, limit: int = 10
):
    logger.info(
        "slack_get_channel_history called team=%s user=%s channel=%s limit=%s",
        team_id,
        current_user_id,
        channel_id,
        limit,
    )
    # Verify user access
    convs = slack.get_user_conversations(team_id, current_user_id)
    channel_ids = [c["id"] for c in convs.get("channels", [])]
    if channel_id not in channel_ids:
        raise HTTPException(
            status_code=403,
            detail=f"User {current_user_id} does not have access to channel {channel_id}",
        )
    return slack.get_channel_history(team_id, channel_id, limit)


# (Other tool definitions remain unchanged) — #

app = FastAPI()
app.mount("/", mcp.sse_app())

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting Slack MCP server (SSE+RPC) on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
