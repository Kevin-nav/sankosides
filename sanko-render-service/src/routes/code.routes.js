/**
 * Code Routes
 */
const express = require('express');
const router = express.Router();
const shikiService = require('../services/shiki.service');
const { log } = require('../utils/logger');

router.post('/render/code', async (req, res) => {
    const { code, language = 'javascript', theme = 'github-dark' } = req.body;

    if (!code) {
        log('WARN', '/render/code', 'Missing code field');
        return res.status(400).json({ success: false, error: 'code field is required' });
    }

    log('DEBUG', '/render/code', `Processing ${language} code (${code.length} chars)`);

    try {
        const html = await shikiService.highlight(code, language, theme);

        log('SUCCESS', '/render/code', `Generated HTML for ${language} (${html.length} bytes)`);

        res.json({
            success: true,
            html: html,
            language,
            theme,
        });

    } catch (error) {
        log('ERROR', '/render/code', `Failed: ${error.message}`);

        // Fallback
        const fallbackHtml = shikiService.getFallback(code);

        res.json({
            success: true,
            html: fallbackHtml,
            language,
            theme,
            fallback: true,
            warning: error.message,
        });
    }
});

module.exports = router;
