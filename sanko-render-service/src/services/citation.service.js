/**
 * Citation Service
 */
const Cite = require('citation-js');
const { log } = require('../utils/logger');

function formatCitation(citation, style = 'apa', index = 0, outputFormat = 'text') {
    try {
        const typeMapping = {
            'Journal': 'article-journal',
            'Book': 'book',
            'Website': 'webpage',
            'Image': 'graphic',
            'Report': 'report',
            'Patent': 'patent',
            'Conference': 'paper-conference'
        };

        // Build CSL-JSON from our metadata (with null checks)
        const authorName = citation.author || (citation.authors && citation.authors[0]) || 'Unknown Author';
        const authorParts = authorName.split(' ');

        const cslData = {
            id: `ref-${index}`,
            type: typeMapping[citation.source] || typeMapping[citation.source_type] || 'webpage',
            title: citation.title || 'Untitled',
            author: [{
                family: authorParts.pop() || 'Unknown',
                given: authorParts.join(' ') || ''
            }],
            issued: { 'date-parts': [[parseInt(citation.year) || new Date().getFullYear()]] },
            DOI: citation.doi,
            URL: citation.url,
            publisher: citation.publisher,
            medium: citation.medium // For images/graphics
        };

        // Use citation-js to format
        const cite = new Cite([cslData]);

        // Choose output format - 'html' includes italics and proper formatting
        const format = outputFormat === 'html' ? 'html' : 'text';

        // Get formatted output
        const formatted = cite.format('bibliography', {
            format: format,
            template: style,
            lang: 'en-US'
        });

        return {
            index,
            original: citation,
            formatted: formatted.trim(),
            style,
            format: outputFormat,
        };

    } catch (err) {
        log('WARN', '/render/citation', `Fallback for citation ${index}: ${err.message}`);
        const fallbackAuthor = citation.author || 'Unknown Author';
        const fallbackYear = citation.year || 'n.d.';
        const fallbackTitle = citation.title || 'Untitled';
        return {
            index,
            original: citation,
            formatted: `${fallbackAuthor} (${fallbackYear}). ${fallbackTitle}.`,
            style,
            fallback: true,
            error: err.message,
        };
    }
}

module.exports = {
    formatCitation
};
