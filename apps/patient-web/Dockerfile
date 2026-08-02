# See apps/staff-web/Dockerfile for why the build context is the repo root.
FROM node:26-slim

RUN corepack enable pnpm && corepack prepare pnpm@9.12.0 --activate

WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages ./packages
COPY apps/staff-web ./apps/staff-web
COPY apps/patient-web ./apps/patient-web
COPY apps/landing ./apps/landing

RUN pnpm install --frozen-lockfile

WORKDIR /workspace/apps/patient-web
EXPOSE 5174

CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0", "--port", "5174"]
