/**
 * Mermaid Service
 */
const { getBrowser } = require('./browser.service');
const { log } = require('../utils/logger');

/**
 * Render Mermaid diagram to SVG via Puppeteer
 */
async function renderMermaid(diagram, theme = 'default') {
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

        return svgContent;

    } finally {
        await page.close();
    }
}

function getFallbackSvg(diagramType, errorMessage) {
    return `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
    <rect width="400" height="200" fill="#fff3cd" rx="8"/>
    <text x="200" y="90" text-anchor="middle" font-family="system-ui" font-size="14" fill="#856404" font-weight="600">
        ${diagramType.toUpperCase()} Diagram
    </text>
    <text x="200" y="115" text-anchor="middle" font-family="system-ui" font-size="11" fill="#856404">
        Rendering failed: ${errorMessage.slice(0, 40)}
    </text>
</svg>`.trim();
}

module.exports = {
    renderMermaid,
    getFallbackSvg
};
