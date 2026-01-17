/**
 * Browser Management Service (Puppeteer)
 */
const puppeteer = require('puppeteer-core');
const path = require('path');
const os = require('os');
const fs = require('fs');
const { log } = require('../utils/logger');

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

    log('SUCCESS', null, 'Browser launched');
    return browser;
}

async function closeBrowser() {
    if (browser) {
        await browser.close();
        browser = null;
        log('SUCCESS', null, 'Browser closed');
    }
}

module.exports = {
    getBrowser,
    closeBrowser,
    findChromePath
};
