/**
 * Request Logger Middleware
 */
const { log, summarizeBody } = require('../utils/logger');

let requestId = 0;

function requestLogger(req, res, next) {
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
}

/**
 * Global Error Handler
 */
function errorHandler(err, req, res, next) {
    log('ERROR', req.path, `Unhandled error: ${err.message}`, { stack: err.stack });
    res.status(500).json({
        success: false,
        error: 'Internal server error',
        message: err.message,
    });
}

module.exports = {
    requestLogger,
    errorHandler
};
