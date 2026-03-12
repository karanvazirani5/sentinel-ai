FROM node:20-alpine AS builder

WORKDIR /app

# When Render Root Directory is "web", the build context is the web/ folder,
# so package.json lives at the root of the context.
COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000

COPY --from=builder /app ./

EXPOSE 3000

CMD ["npm", "run", "start"]


