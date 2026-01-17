/**
 * SankoSlides Rendering Service
 * 
 * This Node.js microservice handles deterministic rendering tasks:
 * - LaTeX → SVG (via mathjax-node)
 * - Mermaid → SVG (via mermaid + puppeteer-core)
 * - Citation metadata → Formatted string (via citation-js)
 * 
 * Reference: alignment_docs/architectural_blueprint.md
 */

const express = require('express');
const cors = require('cors');
const { log, colors, timestamp } = require('./src/utils/logger');
const { requestLogger, errorHandler } = require('./src/middleware/requestLogger');
const { registerRoutes } = require('./src/routes/index.routes');

// Services that need initialization
const shikiService = require('./src/services/shiki.service');
const mathjaxService = require('./src/services/mathjax.service');
const browserService = require('./src/services/browser.service');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Middleware
app.use(requestLogger);

// Routes
registerRoutes(app);

// Error Handler
app.use(errorHandler);

// ============================================================================
// Graceful Shutdown
// ============================================================================

process.on('SIGINT', async () => {
    log('INFO', null, 'Shutting down...');
    await browserService.closeBrowser();
    process.exit(0);
});

// ============================================================================
// Start Server
// ============================================================================

const PORT = process.env.PORT || 3001;

async function startServer() {
    try {
        // Initialize services
        log('INFO', null, 'Initializing services...');

        await shikiService.init().catch(err => log('ERROR', null, `Shiki init failed: ${err.message}`));
        mathjaxService.init(); // Sync init

        // Browser is lazy-loaded on first request, but we can check if Chrome exists
        const chromePath = browserService.findChromePath();

        app.listen(PORT, () => {
            console.log('');
            console.log(`${colors.bright}╔════════════════════════════════════════════════════╗${colors.reset}`);
            console.log(`${colors.bright}║${colors.reset}  ${colors.magenta}🎨 SankoSlides Render Service${colors.reset}                     ${colors.bright}║${colors.reset}`);
            console.log(`${colors.bright}╠════════════════════════════════════════════════════╣${colors.reset}`);
            console.log(`${colors.bright}║${colors.reset}  ${colors.cyan}Port:${colors.reset} ${PORT}                                        ${colors.bright}║${colors.reset}`);
            console.log(`${colors.bright}║${colors.reset}  ${colors.cyan}Time:${colors.reset} ${timestamp()}          ${colors.bright}║${colors.reset}`);
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
    } catch (err) {
        log('ERROR', null, `Startup failed: ${err.message}`);
        process.exit(1);
    }
}

startServer();
