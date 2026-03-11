FROM node:20-alpine AS builder

WORKDIR /app

COPY web/package.json /app/package.json
COPY web/package-lock.json /app/package-lock.json 2>/dev/null || true

RUN npm install

COPY web /app

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000

COPY --from=builder /app /app

EXPOSE 3000

CMD ["npm", "run", "start"]

