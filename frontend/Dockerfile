# Expects a host-side Next build first:
#   cd frontend
#   set NEXT_PUBLIC_API_URL=https://si-erp-api.mushaz.com/api
#   npm ci && npm run build
# Then: docker compose build web
#
# Requires next.config output: "standalone"

FROM node:22-alpine

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --chown=nextjs:nodejs public ./public
COPY --chown=nextjs:nodejs .next/standalone ./
COPY --chown=nextjs:nodejs .next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
