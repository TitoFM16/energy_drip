# Built from the repo root (see docker-compose.yml `context: .`): pnpm
# workspace install needs pnpm-workspace.yaml/pnpm-lock.yaml and every
# declared workspace member present, not just this app's own directory.
FROM node:22-slim

RUN corepack enable pnpm && corepack prepare pnpm@9.12.0 --activate

WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages ./packages
COPY apps/staff-web ./apps/staff-web
COPY apps/patient-web ./apps/patient-web
COPY apps/landing ./apps/landing

RUN pnpm install --frozen-lockfile

WORKDIR /workspace/apps/staff-web
EXPOSE 5173

CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0", "--port", "5173"]
