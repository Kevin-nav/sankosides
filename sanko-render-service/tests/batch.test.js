/**
 * Batch Rendering Tests
 * Tests the /render/batch endpoint for processing multiple items at once
 */
const { api } = require('./setup');

describe('POST /render/batch', () => {
    describe('LaTeX Batch', () => {
        it('should process multiple LaTeX equations', async () => {
            const res = await api()
                .post('/render/batch')
                .send({
                    latex: ['E = mc^2', 'F = ma', 'V = IR']
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.results.latex).toHaveLength(3);
            expect(res.body.results.latex[0].success).toBe(true);
            expect(res.body.results.latex[0].svg).toContain('<svg');
        });

        it('should handle mixed success/failure in batch', async () => {
            const res = await api()
                .post('/render/batch')
                .send({
                    latex: ['E = mc^2', '\\invalid{command}', 'F = ma']
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.results.latex).toHaveLength(3);
            // First and third should succeed
            expect(res.body.results.latex[0].success).toBe(true);
            expect(res.body.results.latex[2].success).toBe(true);
        });
    });

    describe('Citations Batch', () => {
        it('should process multiple citations', async () => {
            const res = await api()
                .post('/render/batch')
                .send({
                    citations: [
                        { author: 'Smith', year: '2020', title: 'Paper 1' },
                        { author: 'Jones', year: '2021', title: 'Paper 2' }
                    ],
                    style: 'apa'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.results.citations).toHaveLength(2);
        });
    });

    describe('Mixed Batch', () => {
        it('should process LaTeX and citations together', async () => {
            const res = await api()
                .post('/render/batch')
                .send({
                    latex: ['E = mc^2'],
                    citations: [{ author: 'Einstein', year: '1905', title: 'Special Relativity' }],
                    style: 'apa'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.results.latex).toHaveLength(1);
            expect(res.body.results.citations).toHaveLength(1);
        });
    });

    describe('Empty Batch', () => {
        it('should handle empty batch request', async () => {
            const res = await api()
                .post('/render/batch')
                .send({})
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.results.latex).toHaveLength(0);
            expect(res.body.results.citations).toHaveLength(0);
        });
    });
});
