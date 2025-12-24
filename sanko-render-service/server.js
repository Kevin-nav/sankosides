/**
 * SankoSlides Rendering Service
 * 
 * This Node.js microservice handles deterministic rendering tasks:
 * - LaTeX → SVG (via mathjax-node)
 * - Mermaid → SVG (via mermaid + puppeteer-core)
 * - Citation metadata → Formatted string (via citation-js)
 * 
 * Why code instead of LLM?
 * - Zero hallucination in formatting
 * - Perfect IEEE/APA/Harvard compliance
 * - Vector-quality math in PowerPoint
 * 
 * Reference: alignment_docs/architectural_blueprint.md
 */

const express = require('express');
const cors = require('cors');
const mj = require('mathjax-node');
const Cite = require('citation-js');
const puppeteer = require('puppeteer-core');
const path = require('path');
const os = require('os');
const { createHighlighter } = require('shiki');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Shiki highlighter instance
let highlighter = null;

// ============================================================================
// LOGGING UTILITIES
// ============================================================================

const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    gray: '\x1b[90m',
};

function timestamp() {
    return new Date().toISOString().replace('T', ' ').slice(0, 19);
}

function log(level, endpoint, message, data = null) {
    const levelColors = {
        INFO: colors.blue,
        SUCCESS: colors.green,
        WARN: colors.yellow,
        ERROR: colors.red,
        DEBUG: colors.gray,
    };

    const color = levelColors[level] || colors.reset;
    const prefix = `${colors.gray}[${timestamp()}]${colors.reset} ${color}[${level}]${colors.reset}`;
    const ep = endpoint ? `${colors.cyan}${endpoint}${colors.reset}` : '';

    console.log(`${prefix} ${ep} ${message}`);

    if (data) {
        if (typeof data === 'object') {
            console.log(`${colors.gray}   └─ ${JSON.stringify(data, null, 2).split('\n').join('\n      ')}${colors.reset}`);
        } else {
            console.log(`${colors.gray}   └─ ${data}${colors.reset}`);
        }
    }
}

// Request counter for tracking
let requestId = 0;

// Middleware to log all requests
app.use((req, res, next) => {
    req.requestId = ++requestId;
    req.startTime = Date.now();

    log('INFO', req.path, `Request #${req.requestId} - ${req.method}`,
        req.body && Object.keys(req.body).length > 0 ? { body: summarizeBody(req.body) } : null);

    // Log response when finished
    res.on('finish', () => {
        const duration = Date.now() - req.startTime;
        const status = res.statusCode;
        const level = status >= 400 ? 'ERROR' : 'SUCCESS';
        log(level, req.path, `Request #${req.requestId} completed - ${status} (${duration}ms)`);
    });

    next();
});

function summarizeBody(body) {
    const summary = {};
    for (const [key, value] of Object.entries(body)) {
        if (typeof value === 'string') {
            summary[key] = value.length > 50 ? value.slice(0, 50) + '...' : value;
        } else if (Array.isArray(value)) {
            summary[key] = `[Array: ${value.length} items]`;
        } else {
            summary[key] = value;
        }
    }
    return summary;
}

// ============================================================================
// Initialize MathJax
// ============================================================================

log('INFO', null, 'Initializing MathJax...');
mj.config({
    MathJax: {
        SVG: {
            font: "TeX"
        }
    }
});
mj.start();
log('SUCCESS', null, 'MathJax initialized');

// ============================================================================
// Initialize Shiki for Code Highlighting
// ============================================================================

async function initializeShiki() {
    log('INFO', null, 'Initializing Shiki...');
    highlighter = await createHighlighter({
        themes: ['github-dark', 'github-light', 'one-dark-pro', 'dracula'],
        langs: ['javascript', 'typescript', 'python', 'java', 'c', 'cpp', 'rust', 'go', 'html', 'css', 'sql', 'bash', 'json'],
    });
    log('SUCCESS', null, 'Shiki initialized with core languages');
}

// Initialize Shiki on startup
initializeShiki().catch(err => log('ERROR', null, `Shiki init failed: ${err.message}`));

// ============================================================================
// Browser Management for Mermaid
// ============================================================================

let browser = null;

// Find Playwright's Chromium installation
function findChromePath() {
    const homeDir = os.homedir();
    const playwrightPath = path.join(homeDir, 'AppData', 'Local', 'ms-playwright');

    // Check for common Playwright Chromium paths
    const possiblePaths = [
        path.join(playwrightPath, 'chromium-1148', 'chrome-win', 'chrome.exe'),
        path.join(playwrightPath, 'chromium-1134', 'chrome-win', 'chrome.exe'),
        path.join(playwrightPath, 'chromium-1124', 'chrome-win', 'chrome.exe'),
        // Generic Chrome paths
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    ];

    const fs = require('fs');
    for (const chromePath of possiblePaths) {
        if (fs.existsSync(chromePath)) {
            return chromePath;
        }
    }

    // Try to find any chromium in playwright folder
    if (fs.existsSync(playwrightPath)) {
        const dirs = fs.readdirSync(playwrightPath);
        for (const dir of dirs) {
            if (dir.startsWith('chromium-')) {
                const chromePath = path.join(playwrightPath, dir, 'chrome-win', 'chrome.exe');
                if (fs.existsSync(chromePath)) {
                    return chromePath;
                }
            }
        }
    }

    return null;
}

async function getBrowser() {
    if (browser && browser.isConnected()) {
        return browser;
    }

    const chromePath = findChromePath();

    if (!chromePath) {
        throw new Error('Chrome/Chromium not found. Install with: playwright install chromium');
    }

    log('INFO', null, `Launching browser from: ${chromePath}`);

    browser = await puppeteer.launch({
        executablePath: chromePath,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    log('SUCCESS', null, 'Browser launched for Mermaid rendering');
    return browser;
}

// ============================================================================
// Health Check
// ============================================================================

app.get('/health', (req, res) => {
    const chromePath = findChromePath();
    res.json({
        status: 'ok',
        service: 'sanko-render-service',
        uptime: process.uptime().toFixed(0) + 's',
        requests_processed: requestId,
        mermaid_ready: !!chromePath,
        chrome_path: chromePath || 'Not found',
    });
});

// ============================================================================
// LaTeX to SVG
// ============================================================================

app.post('/render/latex', async (req, res) => {
    const { latex, display = true } = req.body;

    if (!latex) {
        log('WARN', '/render/latex', 'Missing latex field');
        return res.status(400).json({ success: false, error: 'latex field is required' });
    }

    log('DEBUG', '/render/latex', `Processing: "${latex.slice(0, 60)}${latex.length > 60 ? '...' : ''}"`);

    try {
        // Clean LaTeX input (remove $$ delimiters if present)
        let cleanLatex = latex.trim();
        if (cleanLatex.startsWith('$$') && cleanLatex.endsWith('$$')) {
            cleanLatex = cleanLatex.slice(2, -2);
        } else if (cleanLatex.startsWith('$') && cleanLatex.endsWith('$')) {
            cleanLatex = cleanLatex.slice(1, -1);
        }

        const result = await new Promise((resolve, reject) => {
            mj.typeset({
                math: cleanLatex,
                format: display ? 'TeX' : 'inline-TeX',
                svg: true,
            }, (data) => {
                if (data.errors) {
                    reject(new Error(data.errors.join(', ')));
                } else {
                    resolve(data);
                }
            });
        });

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

// ============================================================================
// Code Syntax Highlighting
// ============================================================================

app.post('/render/code', async (req, res) => {
    const { code, language = 'javascript', theme = 'github-dark' } = req.body;

    if (!code) {
        log('WARN', '/render/code', 'Missing code field');
        return res.status(400).json({ success: false, error: 'code field is required' });
    }

    log('DEBUG', '/render/code', `Processing ${language} code (${code.length} chars)`);

    try {
        if (!highlighter) {
            throw new Error('Shiki not initialized yet. Please wait and retry.');
        }

        const html = highlighter.codeToHtml(code, {
            lang: language,
            theme: theme,
        });

        log('SUCCESS', '/render/code', `Generated HTML for ${language} (${html.length} bytes)`);

        res.json({
            success: true,
            html: html,
            language,
            theme,
        });

    } catch (error) {
        log('ERROR', '/render/code', `Failed: ${error.message}`);

        // Fallback to plain text with basic styling
        const fallbackHtml = `<pre style="background:#1e1e1e;color:#d4d4d4;padding:1rem;border-radius:8px;overflow:auto;"><code>${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`;

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

// ============================================================================
// TikZ/CircuiTikZ to SVG (Circuits, Free Body Diagrams)
// ============================================================================

const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

app.post('/render/tikz', async (req, res) => {
    const { tikz, packages = [] } = req.body;

    if (!tikz) {
        log('WARN', '/render/tikz', 'Missing tikz field');
        return res.status(400).json({ success: false, error: 'tikz field is required' });
    }

    log('DEBUG', '/render/tikz', `Processing TikZ diagram (${tikz.length} chars)`);

    const fs = require('fs');
    const tempDir = os.tmpdir();
    const timestamp = Date.now();
    const baseName = `tikz_${timestamp}`;
    const texFile = path.join(tempDir, `${baseName}.tex`);
    const pdfFile = path.join(tempDir, `${baseName}.pdf`);
    const svgFile = path.join(tempDir, `${baseName}.svg`);

    try {
        // Build LaTeX document with common packages
        const defaultPackages = ['tikz', 'circuitikz', 'amsmath', 'amssymb'];
        const allPackages = [...new Set([...defaultPackages, ...packages])];

        const latexDoc = `\\documentclass[tikz,border=5pt]{standalone}
${allPackages.map(pkg => `\\usepackage{${pkg}}`).join('\n')}
\\usetikzlibrary{arrows.meta,positioning,calc,decorations.pathmorphing,patterns}
\\begin{document}
${tikz}
\\end{document}`;

        // Write .tex file
        fs.writeFileSync(texFile, latexDoc, 'utf8');
        log('DEBUG', '/render/tikz', `Created tex file: ${texFile}`);

        // Compile with pdflatex
        try {
            await execAsync(`pdflatex -interaction=nonstopmode -output-directory="${tempDir}" "${texFile}"`, {
                timeout: 30000,
            });
        } catch (latexError) {
            if (!fs.existsSync(pdfFile)) {
                throw new Error(`LaTeX compilation failed: ${latexError.stderr || latexError.message}`);
            }
        }

        if (!fs.existsSync(pdfFile)) {
            throw new Error('PDF not generated - check LaTeX syntax');
        }

        log('DEBUG', '/render/tikz', 'PDF generated, converting to SVG...');

        // Convert PDF to SVG
        let svgContent;
        try {
            await execAsync(`pdf2svg "${pdfFile}" "${svgFile}"`, { timeout: 10000 });
            svgContent = fs.readFileSync(svgFile, 'utf8');
        } catch (pdf2svgError) {
            try {
                await execAsync(`pdftocairo -svg "${pdfFile}" "${svgFile}"`, { timeout: 10000 });
                svgContent = fs.readFileSync(svgFile, 'utf8');
            } catch (cairoError) {
                throw new Error('pdf2svg/pdftocairo not found. Install: apt-get install pdf2svg poppler-utils');
            }
        }

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

    } finally {
        // Cleanup temp files
        const extensions = ['.tex', '.pdf', '.svg', '.log', '.aux'];
        for (const ext of extensions) {
            const file = path.join(tempDir, `${baseName}${ext}`);
            try { if (fs.existsSync(file)) fs.unlinkSync(file); } catch { }
        }
    }
});

// ============================================================================
// Mermaid to SVG (Real rendering with Puppeteer)
// ============================================================================

app.post('/render/mermaid', async (req, res) => {
    const { diagram, theme = 'default' } = req.body;

    if (!diagram) {
        log('WARN', '/render/mermaid', 'Missing diagram field');
        return res.status(400).json({ success: false, error: 'diagram field is required' });
    }

    const diagramType = diagram.trim().split('\n')[0].split(' ')[0];
    log('DEBUG', '/render/mermaid', `Processing ${diagramType} diagram (${diagram.length} chars)`);

    try {
        const browserInstance = await getBrowser();
        const page = await browserInstance.newPage();

        try {
            // Set viewport
            await page.setViewport({ width: 1200, height: 800 });

            // Escape the diagram for JavaScript string
            const escapedDiagram = diagram
                .replace(/\\/g, '\\\\')
                .replace(/`/g, '\\`')
                .replace(/\$/g, '\\$');

            // HTML using mermaid.render() API directly
            const html = `
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            background: white; 
        }
        #output { 
            font-family: 'Trebuchet MS', Arial, sans-serif;
        }
    </style>
</head>
<body>
    <div id="output"></div>
    <script>
        (async function() {
            try {
                mermaid.initialize({ 
                    startOnLoad: false,
                    theme: '${theme}',
                    securityLevel: 'loose',
                });
                
                const diagramCode = \`${escapedDiagram}\`;
                const { svg } = await mermaid.render('generated-diagram', diagramCode);
                document.getElementById('output').innerHTML = svg;
                window.renderStatus = 'success';
            } catch (error) {
                document.getElementById('output').innerHTML = '<div id="render-error">' + error.message + '</div>';
                window.renderStatus = 'error';
                window.renderError = error.message;
            }
        })();
    </script>
</body>
</html>`;

            await page.setContent(html, { waitUntil: 'networkidle0', timeout: 15000 });

            // Wait for render to complete
            await page.waitForFunction('window.renderStatus !== undefined', { timeout: 10000 });

            // Check for errors
            const renderError = await page.evaluate(() => window.renderError);
            if (renderError) {
                throw new Error(`Mermaid error: ${renderError}`);
            }

            // Wait for SVG to appear
            await page.waitForSelector('#output svg', { timeout: 5000 });

            // Get the SVG content
            const svgContent = await page.evaluate(() => {
                const svg = document.querySelector('#output svg');
                if (!svg) return null;

                // Clone and clean up the SVG
                const clone = svg.cloneNode(true);
                clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

                return clone.outerHTML;
            });

            if (!svgContent) {
                throw new Error('Failed to render Mermaid diagram');
            }

            log('SUCCESS', '/render/mermaid', `Generated SVG for ${diagramType} (${svgContent.length} bytes)`);

            res.json({
                success: true,
                svg: svgContent,
                diagramType,
            });

        } finally {
            await page.close();
        }

    } catch (error) {
        log('ERROR', '/render/mermaid', `Failed: ${error.message}`);

        // Fallback to placeholder if browser fails
        const placeholderSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
    <rect width="400" height="200" fill="#fff3cd" rx="8"/>
    <text x="200" y="90" text-anchor="middle" font-family="system-ui" font-size="14" fill="#856404" font-weight="600">
        ${diagramType.toUpperCase()} Diagram
    </text>
    <text x="200" y="115" text-anchor="middle" font-family="system-ui" font-size="11" fill="#856404">
        Rendering failed: ${error.message.slice(0, 40)}
    </text>
</svg>`.trim();

        res.status(500).json({
            success: false,
            error: error.message,
            svg: placeholderSvg,
            diagramType,
        });
    }
});

// ============================================================================
// Citation Formatting
// ============================================================================

app.post('/render/citation', async (req, res) => {
    const { citations, style = 'apa' } = req.body;

    if (!citations || !Array.isArray(citations)) {
        log('WARN', '/render/citation', 'Missing or invalid citations array');
        return res.status(400).json({
            success: false,
            error: 'citations array is required'
        });
    }

    log('DEBUG', '/render/citation', `Processing ${citations.length} citation(s) in ${style.toUpperCase()} style`);

    try {
        const formattedCitations = citations.map((citation, index) => {
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
                const authorName = citation.author || 'Unknown Author';
                const authorParts = authorName.split(' ');

                const cslData = {
                    id: `ref-${index}`,
                    type: typeMapping[citation.source] || 'webpage',
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

                // Get formatted output
                const formatted = cite.format('bibliography', {
                    format: 'text',
                    template: style,
                    lang: 'en-US'
                });

                log('SUCCESS', '/render/citation', `Formatted: "${formatted.trim().slice(0, 50)}..."`);

                return {
                    index,
                    original: citation,
                    formatted: formatted.trim(),
                    style,
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
        });

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

// ============================================================================
// Batch Render
// ============================================================================

app.post('/render/batch', async (req, res) => {
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
                const result = await new Promise((resolve, reject) => {
                    mj.typeset({
                        math: tex,
                        format: 'TeX',
                        svg: true,
                    }, (data) => {
                        if (data.errors) reject(new Error(data.errors.join(', ')));
                        else resolve(data);
                    });
                });
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
                try {
                    const cslData = {
                        id: `ref-${index}`,
                        type: 'article-journal',
                        title: citation.title,
                        author: [{ family: citation.author }],
                        issued: { 'date-parts': [[parseInt(citation.year)]] },
                    };
                    const cite = new Cite([cslData]);
                    return {
                        original: citation,
                        formatted: cite.format('bibliography', { format: 'text', template: style }).trim(),
                        success: true,
                    };
                } catch (err) {
                    return {
                        original: citation,
                        formatted: `${citation.author} (${citation.year}). ${citation.title}.`,
                        fallback: true,
                        success: true,
                    };
                }
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

// ============================================================================
// Error Handler
// ============================================================================

app.use((err, req, res, next) => {
    log('ERROR', req.path, `Unhandled error: ${err.message}`, { stack: err.stack });
    res.status(500).json({
        success: false,
        error: 'Internal server error',
        message: err.message,
    });
});

// ============================================================================
// Graceful Shutdown
// ============================================================================

process.on('SIGINT', async () => {
    log('INFO', null, 'Shutting down...');
    if (browser) {
        await browser.close();
        log('SUCCESS', null, 'Browser closed');
    }
    process.exit(0);
});

// ============================================================================
// Start Server
// ============================================================================

const PORT = process.env.PORT || 3001;

app.listen(PORT, () => {
    const chromePath = findChromePath();
    console.log('');
    console.log(`${colors.bright}╔════════════════════════════════════════════════════╗${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}  ${colors.magenta}🎨 SankoSlides Render Service${colors.reset}                     ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}╠════════════════════════════════════════════════════╣${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}  ${colors.cyan}Port:${colors.reset} ${PORT}                                        ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}  ${colors.cyan}Time:${colors.reset} ${new Date().toISOString()}          ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}╠════════════════════════════════════════════════════╣${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}  ${colors.green}Endpoints:${colors.reset}                                       ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}    POST ${colors.yellow}/render/latex${colors.reset}    LaTeX → SVG            ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}    POST ${colors.yellow}/render/tikz${colors.reset}     TikZ → SVG             ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}    POST ${colors.yellow}/render/mermaid${colors.reset}  Diagram → SVG          ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}    POST ${colors.yellow}/render/citation${colors.reset} Metadata → String      ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}    POST ${colors.yellow}/render/batch${colors.reset}    Batch Processing       ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}╠════════════════════════════════════════════════════╣${colors.reset}`);
    console.log(`${colors.bright}║${colors.reset}  ${colors.cyan}Mermaid:${colors.reset} ${chromePath ? colors.green + '✓ Ready' : colors.red + '✗ Chrome not found'}${colors.reset}                     ${colors.bright}║${colors.reset}`);
    console.log(`${colors.bright}╚════════════════════════════════════════════════════╝${colors.reset}`);
    console.log('');
    if (chromePath) {
        log('INFO', null, `Chrome found: ${chromePath}`);
    } else {
        log('WARN', null, 'Chrome not found. Mermaid will use fallback. Run: playwright install chromium');
    }
    log('INFO', null, 'Server ready, waiting for requests...');
    console.log('');
});
