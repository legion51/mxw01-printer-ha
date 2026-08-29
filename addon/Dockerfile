FROM node:18-alpine

RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    libpng-dev \
    libjpeg-turbo-dev \
    bash \
    coreutils \
    jq \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --production

COPY server.js ./
COPY run.sh ./
COPY public/ ./public/

RUN chmod +x run.sh

RUN addgroup -g 1000 -S nodejs \
    && adduser -S nodejs -u 1000 \
    && chown -R nodejs:nodejs /app

USER nodejs

EXPOSE 8099

CMD ["./run.sh"]
