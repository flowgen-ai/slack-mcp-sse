# Slack MCP Server (FastMCP + SSE)

This project implements a Slack Model Context Protocol (MCP) server in Python using **FastMCP** and **SSE** under **FastAPI**. It dynamically fetches Slack bot tokens from a PostgreSQL database and exposes a set of tools for interacting with Slack channels and messages on behalf of different teams and users.

## Features

* **Dynamic Bot Tokens:** Retrieves `bot_token` per `team_id` from a Postgres table (`slack_bots`).
* **User‐Scoped Tools:** Tools accept `team_id` and `current_user_id` to ensure operations respect user permissions.
* **Channel Discovery:** Lists public and private channels a user belongs to via Slack’s `users.conversations` API.
* **Conversation History:** Fetches channel history and thread replies with access checks.
* **Message Operations:** Post new messages and thread replies, add reactions.
* **User Info:** List workspace users and fetch detailed profiles.
* **SSE + RPC:** Uses SSE transport for real‐time tool invocation under FastAPI.

## Prerequisites

* Python 3.8+
* PostgreSQL database with table `slack_bots(team_id TEXT PRIMARY KEY, bot_token TEXT)`
* A Slack app with appropriate OAuth scopes:

  * `chat:write`
  * `reactions:write`
  * `conversations.history`, `conversations.replies`
  * `users:read`, `users.profile:read`
  * `users.conversations`

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/slack-mcp-server.git
   cd slack-mcp-server
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in the project root with:

   ```dotenv
   DATABASE_URL=postgresql://user:password@host:port/dbname
   PORT=8000           # optional, default 8000
   ```

5. **Database Table**
   Ensure the `slack_bots` table exists:

   ```sql
   CREATE TABLE slack_bots (
     team_id TEXT PRIMARY KEY,
     bot_token TEXT NOT NULL
   );
   ```

6. **Populate `slack_bots`**

   ```sql
   INSERT INTO slack_bots(team_id, bot_token)
     VALUES ('T1234567890', 'xoxb-...');
   ```

## Running the Server

```bash
uvicorn server:app --reload
```

* The SSE+RPC server is mounted at `/`.
* Connect your MCP client to `http://localhost:8000/` using SSE transport.

## Available Tools

1. **slack\_list\_channels**
   List all public and private channels for a given `team_id` and `current_user_id`.

   ```json
   {
     "tool": "slack_list_channels",
     "arguments": { "team_id": "T123...", "current_user_id": "U456..." }
   }
   ```

2. **slack\_get\_channel\_history**
   Retrieve recent messages from a channel, verifying user access.

   ```json
   {
     "tool": "slack_get_channel_history",
     "arguments": {
       "team_id": "T123...",
       "current_user_id": "U456...",
       "channel_id": "C789...",
       "limit": 20
     }
   }
   ```

3. **slack\_post\_message**
   Post a new message to a channel.

4. **slack\_reply\_to\_thread**
   Reply to a message thread.

5. **slack\_add\_reaction**
   Add an emoji reaction to a message.

6. **slack\_get\_thread\_replies**
   Get all replies in a thread.

7. **slack\_get\_users**
   List all users in the workspace.

8. **slack\_get\_user\_profile**
   Fetch detailed profile information for a user.

*(Refer to `server.py` for full definitions and input schemas.)*

## Error Handling

* Missing or invalid parameters return **HTTP 400**.
* Unauthorized channel access returns **HTTP 403**.
* Missing bot token for a `team_id` raises a `ValueError`.

## License

MIT © Your Organization
