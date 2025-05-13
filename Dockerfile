# ── Stage 1: grab the official Slack MCP server (it has /app/dist + node_modules) ──
FROM mcp/slack AS slack

# ── Stage 2: start from the MCP‐Proxy image (Python) ──────────────────────────────
FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# Install Node + npm so "node" is available for the Slack server
RUN apk update && apk add --no-cache nodejs npm

# Copy the entire Slack app (dist/, node_modules/, etc.) into this image
COPY --from=slack /app /app
WORKDIR /app

# Expose the same SSE port
EXPOSE 3001

# Launch the proxy (SSE→stdio) and then "node dist/index.js"
ENTRYPOINT ["mcp-proxy","--pass-environment","--sse-port","3001","--sse-host","0.0.0.0","--","node","dist/index.js"]
