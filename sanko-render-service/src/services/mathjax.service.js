/**
 * MathJax Service
 */
const mj = require('mathjax-node');
const { log } = require('../utils/logger');

let initialized = false;

function init() {
    if (initialized) return;

    log('INFO', null, 'Initializing MathJax...');
    mj.config({
        MathJax: {
            SVG: {
                font: "TeX"
            }
        }
    });
    mj.start();
    initialized = true;
    log('SUCCESS', null, 'MathJax initialized');
}

async function renderLatex(latex, display = true) {
    if (!initialized) init();

    // Clean LaTeX input (remove $$ delimiters if present)
    let cleanLatex = latex.trim();
    if (cleanLatex.startsWith('$$') && cleanLatex.endsWith('$$')) {
        cleanLatex = cleanLatex.slice(2, -2);
    } else if (cleanLatex.startsWith('$') && cleanLatex.endsWith('$')) {
        cleanLatex = cleanLatex.slice(1, -1);
    }

    return new Promise((resolve, reject) => {
        mj.typeset({
            math: cleanLatex,
            format: display ? 'TeX' : 'inline-TeX',
            svg: true,
        }, (data) => {
            if (data.errors) {
                reject(new Error(data.errors.join(', ')));
            } else {
                resolve({
                    svg: data.svg,
                    width: data.width,
                    height: data.height
                });
            }
        });
    });
}

module.exports = {
    init,
    renderLatex
};
