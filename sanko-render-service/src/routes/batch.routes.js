/**
 * Batch Routes
 */
const express = require('express');
const router = express.Router();
const mathjax = require('../services/mathjax.service');
const citationService = require('../services/citation.service');
const { log } = require('../utils/logger');

router.post('/render/batch', async (req, res) => {
    const { latex = [], diagrams = [], citations = [], style = 'apa' } = req.body;

    log('DEBUG', '/render/batch', `Batch request: ${latex.length} LaTeX, ${diagrams.length} diagrams, ${citations.length} citations`);

    const results = {
        latex: [],
        diagrams: [],
        citations: [],
    };

    try {
        // Process LaTeX
        for (let i = 0; i < latex.length; i++) {
            const tex = latex[i];
            try {
                log('DEBUG', '/render/batch', `  Processing LaTeX ${i + 1}/${latex.length}`);
                const result = await mathjax.renderLatex(tex, true);
                results.latex.push({ input: tex, svg: result.svg, success: true });
            } catch (err) {
                log('ERROR', '/render/batch', `  LaTeX ${i + 1} failed: ${err.message}`);
                results.latex.push({ input: tex, error: err.message, success: false });
            }
        }

        // Process citations
        if (citations.length > 0) {
            log('DEBUG', '/render/batch', `  Processing ${citations.length} citations`);
            results.citations = citations.map((citation, index) => {
                const res = citationService.formatCitation(citation, style, index);
                return {
                    original: citation,
                    formatted: res.formatted,
                    success: !res.error,
                    fallback: res.fallback
                };
            });
        }

        const successCount = results.latex.filter(r => r.success).length +
            results.citations.filter(r => r.success).length;
        const totalCount = results.latex.length + results.citations.length;

        log('SUCCESS', '/render/batch', `Batch complete: ${successCount}/${totalCount} successful`);

        res.json({
            success: true,
            results,
        });

    } catch (error) {
        log('ERROR', '/render/batch', `Batch failed: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message,
        });
    }
});

module.exports = router;
