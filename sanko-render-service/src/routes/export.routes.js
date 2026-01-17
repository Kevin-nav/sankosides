/**
 * Export Routes
 */
const express = require('express');
const router = express.Router();
const exportService = require('../services/export.service');
const { log } = require('../utils/logger');

router.post('/render/svg-to-png', async (req, res) => {
    const { svg, width = 800, height = 600, scale = 2 } = req.body;

    if (!svg) {
        log('WARN', '/render/svg-to-png', 'Missing svg field');
        return res.status(400).json({ success: false, error: 'svg field is required' });
    }

    log('DEBUG', '/render/svg-to-png', `Converting SVG to PNG (${width}x${height} @ ${scale}x scale)`);

    try {
        const result = await exportService.svgToPng(svg, width, height, scale);
        const pngBase64 = result.buffer.toString('base64');

        log('SUCCESS', '/render/svg-to-png', `Generated PNG: ${result.buffer.length} bytes`);

        res.json({
            success: true,
            png_base64: pngBase64,
            width: result.width,
            height: result.height,
            size_bytes: result.buffer.length,
        });

    } catch (error) {
        log('ERROR', '/render/svg-to-png', `Failed: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

router.post('/render/screenshot', async (req, res) => {
    const { html, width = 1280, height = 720 } = req.body;

    if (!html) {
        log('WARN', '/render/screenshot', 'Missing html field');
        return res.status(400).json({ success: false, error: 'html field is required' });
    }

    log('DEBUG', '/render/screenshot', `Capturing screenshot (${width}x${height})`);

    try {
        const pngBuffer = await exportService.captureScreenshot(html, width, height);
        const pngBase64 = pngBuffer.toString('base64');

        log('SUCCESS', '/render/screenshot', `Generated PNG: ${pngBuffer.length} bytes`);

        res.json({
            success: true,
            png_base64: pngBase64,
            width: width,
            height: height,
            size_bytes: pngBuffer.length,
        });

    } catch (error) {
        log('ERROR', '/render/screenshot', `Failed: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

router.post('/render/html-to-pdf', async (req, res) => {
    const {
        html,               // Single HTML or combined slides document
        slides,             // Alternative: array of HTML strings for individual slides
        format = '16:9',    // 16:9, 4:3, A4, Letter
        margin = 0,
        landscape = true,
    } = req.body;

    if (!html && (!slides || !Array.isArray(slides))) {
        log('WARN', '/render/html-to-pdf', 'Missing html or slides field');
        return res.status(400).json({
            success: false,
            error: 'Either html or slides array is required'
        });
    }

    log('DEBUG', '/render/html-to-pdf', `Generating PDF (format: ${format}, slides: ${slides ? slides.length : 1})`);

    try {
        const result = await exportService.htmlToPdf(html, slides, format, margin, landscape);
        const pdfBase64 = result.buffer.toString('base64');

        log('SUCCESS', '/render/html-to-pdf', `Generated PDF: ${result.buffer.length} bytes, ${result.pages} page(s)`);

        res.json({
            success: true,
            pdf_base64: pdfBase64,
            size_bytes: result.buffer.length,
            pages: result.pages,
            format,
        });

    } catch (error) {
        log('ERROR', '/render/html-to-pdf', `Failed: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

module.exports = router;
