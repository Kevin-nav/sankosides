/**
 * Mermaid Routes
 */
const express = require('express');
const router = express.Router();
const mermaidService = require('../services/mermaid.service');
const { log } = require('../utils/logger');

router.post('/render/mermaid', async (req, res) => {
    const { diagram, theme = 'default' } = req.body;

    if (!diagram) {
        log('WARN', '/render/mermaid', 'Missing diagram field');
        return res.status(400).json({ success: false, error: 'diagram field is required' });
    }

    const diagramType = diagram.trim().split('\n')[0].split(' ')[0];
    log('DEBUG', '/render/mermaid', `Processing ${diagramType} diagram (${diagram.length} chars)`);

    try {
        const svgContent = await mermaidService.renderMermaid(diagram, theme);

        log('SUCCESS', '/render/mermaid', `Generated SVG for ${diagramType} (${svgContent.length} bytes)`);

        res.json({
            success: true,
            svg: svgContent,
            diagramType,
        });

    } catch (error) {
        log('ERROR', '/render/mermaid', `Failed: ${error.message}`);

        // Fallback to placeholder
        const placeholderSvg = mermaidService.getFallbackSvg(diagramType, error.message);

        res.status(500).json({
            success: false,
            error: error.message,
            svg: placeholderSvg,
            diagramType,
        });
    }
});

module.exports = router;
