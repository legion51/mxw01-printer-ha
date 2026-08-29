const express = require('express');
const path = require('path');
const cors = require('cors');
const helmet = require('helmet');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.SERVER_PORT || 8099;
const ENABLE_PROXY = process.env.ENABLE_PROXY !== 'false';
const CORS_ORIGIN = process.env.CORS_ALLOW_ORIGIN || '*';

app.use(helmet({
    contentSecurityPolicy: false,
    crossOriginEmbedderPolicy: false
}));

app.use(cors({
    origin: CORS_ORIGIN,
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.static(path.join(__dirname, 'public')));

if (ENABLE_PROXY) {
    app.get('/loadimg', async (req, res) => {
        const imageUrl = req.query.url;
        if (!imageUrl) {
            return res.status(400).send('Missing url parameter');
        }
        try {
            const urlObj = new URL(imageUrl);
            const allowedProtocols = ['http:', 'https:'];
            if (!allowedProtocols.includes(urlObj.protocol)) {
                return res.status(400).send('Invalid protocol');
            }
            const response = await fetch(imageUrl, {
                headers: { 'User-Agent': 'HomeAssistant-MXW01-Printer/1.0' },
                timeout: 10000
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const buffer = await response.buffer();
            res.set({
                'Content-Type': response.headers.get('content-type') || 'image/png',
                'Cache-Control': 'public, max-age=86400'
            });
            res.send(buffer);
        } catch (err) {
            console.error('Proxy error:', err.message);
            res.status(500).send('Failed to fetch image');
        }
    });
}

app.get('/api/status', (req, res) => {
    res.json({
        status: 'running',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    });
});

app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).send('Internal Server Error');
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`MXW01 Printer Server running on port ${PORT}`);
    console.log(`Web interface: http://localhost:${PORT}`);
});

process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down...');
    process.exit(0);
});
