# Stage 1: get the Slack MCP server binary
FROM mcp/slack AS slack

# Stage 2: base on the proxy image
FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# Copy Slack server (wherever its binary lives) into this image
COPY --from=slack /usr/local/bin/mcp-slack /usr/local/bin/mcp-slack
RUN chmod +x /usr/local/bin/mcp-slack

EXPOSE 3001

ENTRYPOINT ["mcp-proxy","--pass-environment","--sse-port","3001","--sse-host","0.0.0.0","--","mcp-slack"]
