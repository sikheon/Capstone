FROM node:20-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install

COPY . .
ARG VITE_SERVER_URL=http://localhost:8000
ENV VITE_SERVER_URL=${VITE_SERVER_URL}
RUN npm run build

# ---- runtime ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
