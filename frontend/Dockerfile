# =============================================================================
# AI Drug Screening Platform — Frontend Dockerfile
# =============================================================================
# 多阶段构建: Node.js 构建 → Nginx 提供静态文件
# =============================================================================

# ── Stage 1: 构建 ──
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .

# 使用 Nginx 代理地址 (避免 CORS)
ENV VITE_API_BASE_URL=http://localhost:3000/api/v1

RUN npm run build

# ── Stage 2: 生产运行 ──
FROM nginx:alpine

# curl for healthcheck
RUN apk add --no-cache curl

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx 配置（SPA 路由 + API 代理）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
