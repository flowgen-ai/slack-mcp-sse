# Stage 1: get the Slack MCP server binary
FROM mcp/slack AS slack

# Stage 2: base on the proxy image
FROM ghcr.io/sparfenyuk/mcp-proxy:latest

# Copy Slack server (wherever its binary lives) into this image
COPY --from=slack . .
RUN chmod +x .

EXPOSE 3001

ENTRYPOINT ["mcp-proxy","--pass-environment","--sse-port","3001","--sse-host","0.0.0.0","--","mcp-slack"]
