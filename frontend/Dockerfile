# Frontend Dockerfile (Vite + Nginx)
FROM node:20 AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* /app/frontend/
WORKDIR /app/frontend
RUN npm install --legacy-peer-deps
COPY frontend /app/frontend
RUN npm run build

FROM nginx:1.25
COPY --from=build /app/frontend/dist /usr/share/nginx/html
# Simple default nginx config
RUN rm /etc/nginx/conf.d/default.conf
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
