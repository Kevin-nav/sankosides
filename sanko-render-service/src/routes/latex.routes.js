/**
 * Latex Routes
 */
const express = require('express');
const router = express.Router();
const mathjax = require('../services/mathjax.service');
const { log } = require('../utils/logger');

router.post('/render/latex', async (req, res) => {
    const { latex, display = true } = req.body;

    if (!latex) {
        log('WARN', '/render/latex', 'Missing latex field');
        return res.status(400).json({ success: false, error: 'latex field is required' });
    }

    log('DEBUG', '/render/latex', `Processing: "${latex.slice(0, 60)}${latex.length > 60 ? '...' : ''}"`);

    try {
        const result = await mathjax.renderLatex(latex, display);

        log('SUCCESS', '/render/latex', `Generated SVG: ${result.width} x ${result.height}`);

        res.json({
            success: true,
            svg: result.svg,
            width: result.width,
            height: result.height,
        });

    } catch (error) {
        log('ERROR', '/render/latex', `Failed: ${error.message}`, { latex: latex.slice(0, 100) });
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

module.exports = router;
