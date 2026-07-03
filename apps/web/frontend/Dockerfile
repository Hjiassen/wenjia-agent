FROM node:20-alpine AS build

WORKDIR /app

COPY apps/web/frontend/package.json apps/web/frontend/package-lock.json ./
RUN npm ci

COPY apps/web/frontend ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY apps/web/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
