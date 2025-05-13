# ── pull in the official Slack MCP server (with all code & deps in /app) ─────
FROM mcp/slack AS slack

# ── pull in the MCP-Proxy bridge ────────────────────────────────────────────
FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# copy the entire Slack server app (/app contains dist/, node_modules/, etc)
COPY --from=slack /app /app
WORKDIR /app

# expose SSE port
EXPOSE 3001

# one-line ENTRYPOINT: run the proxy (SSE→stdio) and spawn Slack via node
ENTRYPOINT ["mcp-proxy","--pass-environment","--sse-port","3001","--sse-host","0.0.0.0","--","node","dist/index.js"]
