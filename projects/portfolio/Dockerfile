# syntax=docker/dockerfile:1.7

# Stage 1 — build the static site
FROM node:20-alpine AS builder
WORKDIR /app

# Optional GitHub PAT for authenticated API calls during build
# (5000/hr authenticated vs 60/hr unauthenticated).
ARG GITHUB_TOKEN
ENV GITHUB_TOKEN=$GITHUB_TOKEN

COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi

COPY . .
RUN npm run build

# Stage 2 — serve via nginx
FROM nginx:1.27-alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://localhost/ >/dev/null || exit 1
