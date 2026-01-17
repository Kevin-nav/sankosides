/**
 * Logging Utilities
 */

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

module.exports = {
    colors,
    timestamp,
    log,
    summarizeBody
};
