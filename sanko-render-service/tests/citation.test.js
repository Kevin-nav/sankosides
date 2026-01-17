/**
 * Citation Formatting Tests
 * Tests the /render/citation endpoint for various citation styles
 */
const { api } = require('./setup');

describe('POST /render/citation', () => {
    describe('APA Style', () => {
        it('should format journal article in APA style', async () => {
            const res = await api()
                .post('/render/citation')
                .send({
                    citations: [{
                        author: 'Smith, John',
                        year: '2023',
                        title: 'Deep Learning for NLP',
                        source: 'Journal',
                        doi: '10.1234/example'
                    }],
                    style: 'apa'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.citations).toHaveLength(1);
            expect(res.body.citations[0].formatted).toBeDefined();
            expect(res.body.style).toBe('apa');
        });

        it('should format book in APA style', async () => {
            const res = await api()
                .post('/render/citation')
                .send({
                    citations: [{
                        author: 'Johnson, Mary',
                        year: '2022',
                        title: 'Introduction to Machine Learning',
                        source: 'Book'
                    }],
                    style: 'apa'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.citations[0].formatted).toContain('Mary');
        });

        it('should format image/graphic in APA style', async () => {
            const res = await api()
                .post('/render/citation')
                .send({
                    citations: [{
                        author: 'NASA',
                        year: '2022',
                        title: 'James Webb Image',
                        source: 'Image',
                        medium: 'Digital Image'
                    }],
                    style: 'apa'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('IEEE Style', () => {
        it('should format citation in IEEE style', async () => {
            const res = await api()
                .post('/render/citation')
                .send({
                    citations: [{
                        author: 'Chen, Wei',
                        year: '2024',
                        title: 'Efficient Transformers',
                        source: 'Journal'
                    }],
                    style: 'ieee'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.style).toBe('ieee');
        });
    });

    describe('Harvard Style', () => {
        it('should format citation in Harvard style', async () => {
            const res = await api()
                .post('/render/citation')
                .send({
                    citations: [{
                        author: 'Mozilla',
                        year: '2024',
                        title: 'MDN Web Docs',
                        source: 'Website',
                        url: 'https://developer.mozilla.org'
                    }],
                    style: 'harvard1'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Multiple Citations', () => {
        it('should format multiple citations at once', async () => {
            const res = await api()
                .post('/render/citation')
                .send({
                    citations: [
                        { author: 'Author One', year: '2020', title: 'First Paper', source: 'Journal' },
                        { author: 'Author Two', year: '2021', title: 'Second Paper', source: 'Journal' },
                        { author: 'Author Three', year: '2022', title: 'Third Paper', source: 'Book' }
                    ],
                    style: 'apa'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.citations).toHaveLength(3);
        });
    });

    describe('Fallback Handling', () => {
        it('should use fallback for missing author', async () => {
            const res = await api()
                .post('/render/citation')
                .send({
                    citations: [{
                        year: '2023',
                        title: 'Anonymous Paper',
                        source: 'Journal'
                    }],
                    style: 'apa'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            // Should still return a formatted citation
            expect(res.body.citations[0].formatted).toBeDefined();
        });
    });

    describe('Error Handling', () => {
        it('should return 400 when citations array is missing', async () => {
            const res = await api()
                .post('/render/citation')
                .send({ style: 'apa' })
                .expect(400);

            expect(res.body.success).toBe(false);
            expect(res.body.error).toContain('citations');
        });

        it('should return 400 when citations is not an array', async () => {
            const res = await api()
                .post('/render/citation')
                .send({ citations: 'not an array' })
                .expect(400);

            expect(res.body.success).toBe(false);
        });
    });
});
