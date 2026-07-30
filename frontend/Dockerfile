# =============================================================================
# HRMS Frontend — Production Docker Image (Next.js 16 / React 19)
#
# Multi-stage build:
#   Stage 1 (deps)    – install dependencies with npm ci for reproducibility
#   Stage 2 (builder) – build the Next.js standalone output
#   Stage 3 (runner)  – minimal production runtime (~200 MB)
#
# Standalone output mode (next.config.ts: output:'standalone') copies only
# the files required at runtime, drastically reducing image size.
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps

# Install libc6-compat for compatibility with Alpine
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files first for better layer caching
COPY package.json package-lock.json* ./

# Clean install — uses lockfile for reproducible builds
RUN npm ci --ignore-scripts

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Build the application
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy installed dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy all source files
COPY . .

# Build-time environment variables (baked into the JS bundle)
# Override via --build-arg or Jenkins credentials
ARG NEXT_PUBLIC_API_URL=http://192.168.1.60:10016
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Disable Next.js telemetry in CI
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application (produces .next/standalone/)
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: Production runtime
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Run as non-root user for security
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy only what's needed from the standalone build
COPY --from=builder /app/public ./public

# Standalone output already contains the server.js entry point
# and all required node_modules (trimmed to production-only)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# Next.js runs on port 3000 by default; host port 10015 maps to this
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check — verifies the app is serving requests
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
