/**
 * SankoSlides Math Loader
 * Auto-detects and renders LaTeX equations using KaTeX.
 * Supports inline ($...$) and block ($$...$$) syntax.
 */

document.addEventListener("DOMContentLoaded", function () {
    // Only run if KaTeX is loaded
    if (typeof renderMathInElement === 'undefined') {
        console.warn("KaTeX not loaded, skipping math rendering");
        return;
    }

    renderMathInElement(document.body, {
        delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\(", right: "\\)", display: false },
            { left: "\\[", right: "\\]", display: true }
        ],
        throwOnError: false,
        errorColor: "#cc0000",
        strict: "ignore"
    });

    // Adjust font size for math in big headers
    document.querySelectorAll('h1 .katex').forEach(el => {
        el.style.fontSize = '0.9em';
    });
});
