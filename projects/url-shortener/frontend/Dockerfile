# syntax=docker/dockerfile:1.7

# Stage 1 — build the static bundle
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi
COPY tsconfig*.json vite.config.ts index.html ./
COPY src ./src
RUN npm run build

# Stage 2 — serve via nginx with reverse-proxy to the backend
FROM nginx:1.27-alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://localhost/ >/dev/null || exit 1
