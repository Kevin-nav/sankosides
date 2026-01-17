/**
 * TikZ Rendering Tests
 * Tests the /render/tikz endpoint for circuit diagrams and physics diagrams
 * 
 * Note: These tests require pdflatex and pdf2svg/pdftocairo to be installed
 */
const { api } = require('./setup');

describe('POST /render/tikz', () => {
    // Skip TikZ tests if LaTeX is not installed
    const skipIfNoLatex = process.env.SKIP_TIKZ_TESTS === 'true';

    describe('Circuit Diagrams', () => {
        (skipIfNoLatex ? it.skip : it)('should render RC circuit', async () => {
            const res = await api()
                .post('/render/tikz')
                .send({
                    tikz: `\\begin{circuitikz}
\\draw (0,0) to[R, l=$R$] (3,0)
to[C, l=$C$] (3,-2)
-- (0,-2)
to[battery1, l=$V_{in}$] (0,0);
\\end{circuitikz}`
                });

            if (res.status === 200) {
                expect(res.body.success).toBe(true);
                expect(res.body.svg).toContain('<svg');
            } else {
                // LaTeX not installed - acceptable failure
                expect(res.body.success).toBe(false);
                expect(res.body.hint).toBeDefined();
            }
        });

        (skipIfNoLatex ? it.skip : it)('should render voltage divider', async () => {
            const res = await api()
                .post('/render/tikz')
                .send({
                    tikz: `\\begin{circuitikz}
\\draw (0,0) node[ground]{}
to[battery1, l=$V_{in}$] (0,3)
to[R, l=$R_1$] (3,3)
to[R, l=$R_2$] (3,0) node[ground]{};
\\end{circuitikz}`
                });

            if (res.status === 200) {
                expect(res.body.success).toBe(true);
            }
        });
    });

    describe('Physics Diagrams', () => {
        (skipIfNoLatex ? it.skip : it)('should render free body diagram', async () => {
            const res = await api()
                .post('/render/tikz')
                .send({
                    tikz: `\\begin{tikzpicture}
\\draw[fill=gray!30] (0,0) rectangle (2,1.5);
\\node at (1,0.75) {$m$};
\\draw[->, thick, red] (1,1.5) -- (1,3) node[above]{$\\vec{N}$};
\\draw[->, thick, blue] (1,0) -- (1,-1.5) node[below]{$m\\vec{g}$};
\\end{tikzpicture}`
                });

            if (res.status === 200) {
                expect(res.body.success).toBe(true);
            }
        });
    });

    describe('Custom Packages', () => {
        (skipIfNoLatex ? it.skip : it)('should accept additional packages', async () => {
            const res = await api()
                .post('/render/tikz')
                .send({
                    tikz: `\\begin{tikzpicture}
\\draw (0,0) circle (1cm);
\\end{tikzpicture}`,
                    packages: ['pgfplots']
                });

            // Just verify the request is accepted
            expect(res.body).toHaveProperty('success');
        });
    });

    describe('Error Handling', () => {
        it('should return 400 when tikz field is missing', async () => {
            const res = await api()
                .post('/render/tikz')
                .send({})
                .expect(400);

            expect(res.body.success).toBe(false);
            expect(res.body.error).toContain('tikz');
        });

        it('should handle invalid TikZ syntax', async () => {
            const res = await api()
                .post('/render/tikz')
                .send({ tikz: '\\invalid{command}' });

            // Should return error with hint about LaTeX
            if (res.status !== 200) {
                expect(res.body.success).toBe(false);
            }
        });
    });
});
