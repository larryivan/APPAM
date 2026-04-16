FROM node:20-alpine AS build

WORKDIR /app/frontend

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable \
  && corepack prepare pnpm@10.10.0 --activate \
  && pnpm install --frozen-lockfile

COPY frontend /app/frontend
RUN pnpm build

FROM nginx:1.27-alpine AS runtime

COPY docker/website/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
