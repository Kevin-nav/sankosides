/**
 * Export Rendering Tests
 * Tests the /render/svg-to-png, /render/screenshot, and /render/html-to-pdf endpoints
 * 
 * Note: These tests require Chrome/Chromium to be available
 */
const { api } = require('./setup');

describe('Export Endpoints', () => {
    describe('POST /render/svg-to-png', () => {
        it('should convert SVG to PNG', async () => {
            const testSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
<circle cx="50" cy="50" r="40" fill="red"/>
</svg>`;

            const res = await api()
                .post('/render/svg-to-png')
                .send({ svg: testSvg })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.png_base64).toBeDefined();
            expect(res.body.size_bytes).toBeGreaterThan(0);
        });

        it('should support custom dimensions', async () => {
            const testSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" fill="blue"/>
</svg>`;

            const res = await api()
                .post('/render/svg-to-png')
                .send({ svg: testSvg, width: 400, height: 400, scale: 1 })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should support scale factor', async () => {
            const testSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" fill="green"/>
</svg>`;

            const res = await api()
                .post('/render/svg-to-png')
                .send({ svg: testSvg, scale: 3 })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should return 400 when svg field is missing', async () => {
            const res = await api()
                .post('/render/svg-to-png')
                .send({})
                .expect(400);

            expect(res.body.success).toBe(false);
            expect(res.body.error).toContain('svg');
        });
    });

    describe('POST /render/screenshot', () => {
        it('should capture HTML as PNG', async () => {
            const testHtml = `<!DOCTYPE html>
<html>
<body style="background: #333; color: white; padding: 20px;">
<h1>Test Slide</h1>
<p>This is a test.</p>
</body>
</html>`;

            const res = await api()
                .post('/render/screenshot')
                .send({ html: testHtml })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.png_base64).toBeDefined();
            expect(res.body.width).toBe(1280);
            expect(res.body.height).toBe(720);
        });

        it('should support custom dimensions', async () => {
            const testHtml = `<html><body><h1>Test</h1></body></html>`;

            const res = await api()
                .post('/render/screenshot')
                .send({ html: testHtml, width: 1920, height: 1080 })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.width).toBe(1920);
            expect(res.body.height).toBe(1080);
        });

        it('should return 400 when html field is missing', async () => {
            const res = await api()
                .post('/render/screenshot')
                .send({})
                .expect(400);

            expect(res.body.success).toBe(false);
            expect(res.body.error).toContain('html');
        });
    });

    describe('POST /render/html-to-pdf', () => {
        it('should convert HTML to PDF', async () => {
            const testHtml = `<!DOCTYPE html>
<html>
<body>
<h1>Test PDF</h1>
<p>This is a test document.</p>
</body>
</html>`;

            const res = await api()
                .post('/render/html-to-pdf')
                .send({ html: testHtml })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.pdf_base64).toBeDefined();
            expect(res.body.size_bytes).toBeGreaterThan(0);
            expect(res.body.pages).toBe(1);
        });

        it('should support slides array', async () => {
            const res = await api()
                .post('/render/html-to-pdf')
                .send({
                    slides: [
                        '<h1>Slide 1</h1>',
                        '<h1>Slide 2</h1>',
                        '<h1>Slide 3</h1>'
                    ]
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.pages).toBe(3);
        });

        it('should support different formats', async () => {
            const testHtml = '<h1>Test</h1>';

            const formats = ['16:9', '4:3', 'A4', 'Letter'];

            for (const format of formats) {
                const res = await api()
                    .post('/render/html-to-pdf')
                    .send({ html: testHtml, format })
                    .expect(200);

                expect(res.body.success).toBe(true);
                expect(res.body.format).toBe(format);
            }
        });

        it('should return 400 when neither html nor slides provided', async () => {
            const res = await api()
                .post('/render/html-to-pdf')
                .send({})
                .expect(400);

            expect(res.body.success).toBe(false);
        });
    });
});
