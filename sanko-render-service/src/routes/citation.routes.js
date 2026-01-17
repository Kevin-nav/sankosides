/**
 * Citation Routes
 */
const express = require('express');
const router = express.Router();
const citationService = require('../services/citation.service');
const { log } = require('../utils/logger');

router.post('/render/citation', async (req, res) => {
    const { citations, style = 'apa', format = 'html' } = req.body;

    if (!citations || !Array.isArray(citations)) {
        log('WARN', '/render/citation', 'Missing or invalid citations array');
        return res.status(400).json({
            success: false,
            error: 'citations array is required'
        });
    }

    log('DEBUG', '/render/citation', `Processing ${citations.length} citation(s) in ${style.toUpperCase()} style (format: ${format})`);

    try {
        const formattedCitations = citations.map((citation, index) =>
            citationService.formatCitation(citation, style, index, format)
        );

        res.json({
            success: true,
            citations: formattedCitations,
            style,
        });

    } catch (error) {
        log('ERROR', '/render/citation', `Failed: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

module.exports = router;
