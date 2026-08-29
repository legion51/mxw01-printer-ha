const express = require('express');
const path = require('path');
const cors = require('cors');
const helmet = require('helmet');

const app = express();
const PORT = process.env.SERVER_PORT || 8099;
const ENABLE_PROXY = process.env.ENABLE_PROXY !== 'false';
const CORS_ORIGIN = process.env.CORS_ALLOW_ORIGIN || '*';

// Security
app.use(helmet({
    contentSecurityPolicy: false,
    crossOriginEmbedderPolicy: false
}));

// CORS for Web Bluetooth
app.use(cors({
    origin: CORS_ORIGIN,
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

// Static files
app.use(express.static(path.join(__dirname, 'public')));

// Proxy for image loading
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
                headers: {
                    'User-Agent': 'HomeAssistant-MXW01-Printer/1.0'
                },
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

// API for Home Assistant
app.get('/api/status', (req, res) => {
    res.json({
        status: 'running',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    });
});

app.post('/api/print', express.json(), async (req, res) => {
    try {
        const { text, params } = req.body;
        if (!text) {
            return res.status(400).json({ error: 'No text provided' });
        }
        res.json({
            status: 'queued',
            message: 'Print job queued (Web Bluetooth required on client)'
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Error handling
app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).send('Internal Server Error');
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`MXW01 Printer Server running on port ${PORT}`);
    console.log(`Web interface: http://localhost:${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down...');
    process.exit(0);
});