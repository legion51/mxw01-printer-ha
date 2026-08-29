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

# Create working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci --production

# Copy application files
COPY server.js ./
COPY run.sh ./
COPY public/ ./public/

# Make run script executable
RUN chmod +x run.sh

# Create non-root user
RUN addgroup -g 1000 -S nodejs \
    && adduser -S nodejs -u 1000 \
    && chown -R nodejs:nodejs /app

USER nodejs

EXPOSE 8099

CMD ["./run.sh"]