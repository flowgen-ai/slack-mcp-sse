# Use the official MCP Proxy as base
FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# Install only the Docker CLI (no daemon) so the proxy can spawn sibling containers
RUN apk update && apk add --no-cache docker-cli        # install docker-cli :contentReference[oaicite:1]{index=1}

# Expose the SSE port
EXPOSE 3001

# Launch mcp-proxy in stdio→SSE mode, spawning the official mcp/slack image
ENTRYPOINT ["mcp-proxy","--pass-environment","--sse-port","3001","--sse-host","0.0.0.0","--","docker","run","--rm","-i","-e","SLACK_BOT_TOKEN","-e","SLACK_TEAM_ID","mcp/slack"]
