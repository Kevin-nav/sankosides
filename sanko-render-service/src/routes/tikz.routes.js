/**
 * TikZ Routes
 */
const express = require('express');
const router = express.Router();
const tikzService = require('../services/tikz.service');
const { log } = require('../utils/logger');

router.post('/render/tikz', async (req, res) => {
    const { tikz, packages = [] } = req.body;

    if (!tikz) {
        log('WARN', '/render/tikz', 'Missing tikz field');
        return res.status(400).json({ success: false, error: 'tikz field is required' });
    }

    log('DEBUG', '/render/tikz', `Processing TikZ diagram (${tikz.length} chars)`);

    try {
        const svgContent = await tikzService.renderTikz(tikz, packages);

        log('SUCCESS', '/render/tikz', `Generated SVG (${svgContent.length} bytes)`);

        res.json({
            success: true,
            svg: svgContent,
        });

    } catch (error) {
        log('ERROR', '/render/tikz', `Failed: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message,
            hint: 'Install: apt-get install texlive-pictures texlive-latex-extra pdf2svg',
        });
    }
});

module.exports = router;
