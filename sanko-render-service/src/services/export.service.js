/**
 * Export Service
 */
const { getBrowser } = require('./browser.service');
const { log } = require('../utils/logger');

async function svgToPng(svg, width, height, scale) {
    const browserInstance = await getBrowser();
    const page = await browserInstance.newPage();

    try {
        // Set viewport for high-res rendering
        await page.setViewport({
            width: width * scale,
            height: height * scale,
            deviceScaleFactor: scale,
        });

        // Create minimal HTML with the SVG
        const html = `
<!DOCTYPE html>
<html>
<head>
    <style>
        * { margin: 0; padding: 0; }
        body { 
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            width: ${width}px;
            height: ${height}px;
        }
        svg {
            max-width: 100%;
            max-height: 100%;
        }
    </style>
</head>
<body>
    ${svg}
</body>
</html>`;

        await page.setContent(html, { waitUntil: 'networkidle0', timeout: 10000 });

        // Wait for SVG to render
        await page.waitForSelector('svg', { timeout: 5000 });

        // Get bounding box of SVG for optimal clipping
        const svgBounds = await page.evaluate(() => {
            const svg = document.querySelector('svg');
            if (!svg) return null;
            const rect = svg.getBoundingClientRect();
            return {
                x: Math.max(0, rect.x),
                y: Math.max(0, rect.y),
                width: Math.min(rect.width, window.innerWidth),
                height: Math.min(rect.height, window.innerHeight),
            };
        });

        // Capture as PNG
        const pngBuffer = await page.screenshot({
            type: 'png',
            clip: svgBounds || { x: 0, y: 0, width, height },
            omitBackground: false,
        });

        return {
            buffer: pngBuffer,
            width: svgBounds ? svgBounds.width * scale : width * scale,
            height: svgBounds ? svgBounds.height * scale : height * scale
        };

    } finally {
        await page.close();
    }
}

async function captureScreenshot(html, width, height) {
    const browserInstance = await getBrowser();
    const page = await browserInstance.newPage();

    try {
        // Set viewport for slide dimensions
        await page.setViewport({
            width: width,
            height: height,
            deviceScaleFactor: 2, // 2x for crisp rendering
        });

        // Set the HTML content
        await page.setContent(html, {
            waitUntil: 'networkidle0',
            timeout: 30000,
        });

        // Wait for fonts and images to load
        await page.evaluate(() => document.fonts.ready);

        // Small delay to ensure rendering is complete
        await new Promise(r => setTimeout(r, 200));

        // Capture as PNG
        const pngBuffer = await page.screenshot({
            type: 'png',
            clip: { x: 0, y: 0, width, height },
            omitBackground: false,
        });

        return pngBuffer;

    } finally {
        await page.close();
    }
}

async function htmlToPdf(html, slides, format = '16:9', margin = 0, landscape = true) {
    const browserInstance = await getBrowser();
    const page = await browserInstance.newPage();

    try {
        // Page dimensions based on format
        const dimensions = {
            '16:9': { width: 1920, height: 1080 },
            '4:3': { width: 1600, height: 1200 },
            'A4': { width: 794, height: 1123 },      // A4 at 96 DPI
            'Letter': { width: 816, height: 1056 },  // Letter at 96 DPI
        };

        const { width, height } = dimensions[format] || dimensions['16:9'];

        await page.setViewport({ width, height });

        // If slides array provided, combine into single document
        let fullHtml;
        if (slides && slides.length > 0) {
            fullHtml = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: white; }
        .slide {
            width: ${width}px;
            height: ${height}px;
            page-break-after: always;
            overflow: hidden;
            position: relative;
        }
        .slide:last-child {
            page-break-after: auto;
        }
    </style>
</head>
<body>
${slides.map((slideHtml, i) => `<div class="slide" data-slide="${i + 1}">${slideHtml}</div>`).join('\n')}
</body>
</html>`;
        } else {
            fullHtml = html;
        }

        await page.setContent(fullHtml, {
            waitUntil: 'networkidle0',
            timeout: 30000
        });

        // Wait for any lazy-loaded content
        await new Promise(resolve => setTimeout(resolve, 500));

        // Generate PDF
        const pdfBuffer = await page.pdf({
            width: `${width}px`,
            height: `${height}px`,
            margin: typeof margin === 'object' ? margin : { top: margin, right: margin, bottom: margin, left: margin },
            printBackground: true,
            preferCSSPageSize: false,
            landscape: format === '16:9' || format === '4:3' ? landscape : false,
        });

        return {
            buffer: pdfBuffer,
            pages: slides ? slides.length : 1
        };

    } finally {
        await page.close();
    }
}

module.exports = {
    svgToPng,
    captureScreenshot,
    htmlToPdf
};
