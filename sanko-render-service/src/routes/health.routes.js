/**
 * Health Routes
 */
const express = require('express');
const router = express.Router();
const { findChromePath } = require('../services/browser.service');

// Request counter is global across the app, 
// for simplicity in modular split we might just track requests locally or ignore uptime accuracy relative to process start
// But to keep identical behavior, we'll access the process.uptime()

router.get('/health', (req, res) => {
    const chromePath = findChromePath();
    res.json({
        status: 'ok',
        service: 'sanko-render-service',
        uptime: process.uptime().toFixed(0) + 's',
        requests_processed: req.requestId || 0, // Injected by middleware
        mermaid_ready: !!chromePath,
        chrome_path: chromePath || 'Not found',
    });
});

module.exports = router;
