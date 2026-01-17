/**
 * TikZ Service
 */
const { exec } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { log } = require('../utils/logger');

const execAsync = promisify(exec);

async function renderTikz(tikz, packages = []) {
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

        return svgContent;

    } finally {
        // Cleanup temp files
        const extensions = ['.tex', '.pdf', '.svg', '.log', '.aux'];
        for (const ext of extensions) {
            const file = path.join(tempDir, `${baseName}${ext}`);
            try { if (fs.existsSync(file)) fs.unlinkSync(file); } catch { }
        }
    }
}

module.exports = {
    renderTikz
};
