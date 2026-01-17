/**
 * LaTeX Rendering Tests
 * Tests the /render/latex endpoint for various equation types
 */
const { api } = require('./setup');

describe('POST /render/latex', () => {
    describe('Basic Equations', () => {
        it('should render simple equation (E=mc²)', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: 'E = mc^2' })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.svg).toContain('<svg');
            expect(res.body.svg).toContain('</svg>');
            expect(res.body).toHaveProperty('width');
            expect(res.body).toHaveProperty('height');
        });

        it('should render quadratic formula', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: 'x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}' })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.svg).toContain('<svg');
        });

        it('should render Euler\'s identity', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: 'e^{i\\pi} + 1 = 0' })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.svg).toContain('<svg');
        });
    });

    describe('Advanced Equations', () => {
        it('should render Schrödinger equation', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: 'i\\hbar\\frac{\\partial}{\\partial t}\\Psi = \\hat{H}\\Psi' })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should render matrix', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: '\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}' })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should render integral', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: '\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}' })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should render summation', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: '\\sum_{n=0}^{\\infty} \\frac{1}{n!}' })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Input Handling', () => {
        it('should strip $$ delimiters', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: '$$E = mc^2$$' })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should strip $ delimiters', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: '$E = mc^2$' })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should support display mode flag', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: 'x^2', display: false })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Error Handling', () => {
        it('should return 400 when latex field is missing', async () => {
            const res = await api()
                .post('/render/latex')
                .send({})
                .expect(400);

            expect(res.body.success).toBe(false);
            expect(res.body.error).toContain('latex');
        });

        it('should handle invalid LaTeX gracefully', async () => {
            const res = await api()
                .post('/render/latex')
                .send({ latex: '\\invalid{command}' });

            // Should either succeed with fallback or return error
            expect(res.body).toHaveProperty('success');
        });
    });
});
