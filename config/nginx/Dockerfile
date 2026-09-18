FROM node:20-bookworm as builder
WORKDIR /app
COPY ./frontend/ ./
RUN yarn install && yarn build

FROM nginx:1.20.1
COPY --from=builder /app/dist /etc/nginx/html/
CMD ["nginx", "-g", "daemon off;"]
