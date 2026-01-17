/**
 * Shiki Service
 */
const { createHighlighter } = require('shiki');
const { log } = require('../utils/logger');

let highlighter = null;

async function init() {
    if (highlighter) return;

    log('INFO', null, 'Initializing Shiki...');
    highlighter = await createHighlighter({
        themes: ['github-dark', 'github-light', 'one-dark-pro', 'dracula'],
        langs: ['javascript', 'typescript', 'python', 'java', 'c', 'cpp', 'rust', 'go', 'html', 'css', 'sql', 'bash', 'json'],
    });
    log('SUCCESS', null, 'Shiki initialized with core languages');
}

/**
 * Highlight code
 */
async function highlight(code, language = 'javascript', theme = 'github-dark') {
    if (!highlighter) {
        throw new Error('Shiki not initialized yet. Please wait and retry.');
    }

    // Try to sanitize language (shiki is strict)
    // If language is not found, it will throw, handled by caller or fallback

    return highlighter.codeToHtml(code, {
        lang: language,
        theme: theme,
    });
}

/**
 * Generate fallback HTML for code blocks
 */
function getFallback(code) {
    return `<pre style="background:#1e1e1e;color:#d4d4d4;padding:1rem;border-radius:8px;overflow:auto;"><code>${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`;
}

module.exports = {
    init,
    highlight,
    getFallback
};
