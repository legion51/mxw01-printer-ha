FROM node:18-alpine

# Install build dependencies
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

# Copy package files
COPY package.json package-lock.json ./

# Use npm install instead of npm ci (more forgiving)
RUN npm install --production

# Copy application files
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