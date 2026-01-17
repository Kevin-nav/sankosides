/**
 * Routes Index
 */
const healthRoutes = require('./health.routes');
const latexRoutes = require('./latex.routes');
const codeRoutes = require('./code.routes');
const citationRoutes = require('./citation.routes');
const mermaidRoutes = require('./mermaid.routes');
const tikzRoutes = require('./tikz.routes');
const batchRoutes = require('./batch.routes');
const exportRoutes = require('./export.routes');

function registerRoutes(app) {
    app.use('/', healthRoutes);
    app.use('/', latexRoutes);
    app.use('/', codeRoutes);
    app.use('/', citationRoutes);
    app.use('/', mermaidRoutes);
    app.use('/', tikzRoutes);
    app.use('/', batchRoutes);
    app.use('/', exportRoutes);
}

module.exports = { registerRoutes };
