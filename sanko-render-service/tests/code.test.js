/**
 * Code Syntax Highlighting Tests
 * Tests the /render/code endpoint for Shiki-based syntax highlighting
 */
const { api } = require('./setup');

describe('POST /render/code', () => {
    describe('Language Support', () => {
        it('should highlight JavaScript code', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'const x = 42;\nconsole.log(x);',
                    language: 'javascript'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.html).toContain('<pre');
            expect(res.body.language).toBe('javascript');
        });

        it('should highlight Python code', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'def hello():\n    print("Hello")',
                    language: 'python'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.html).toContain('<pre');
        });

        it('should highlight Rust code', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'fn main() {\n    println!("Hello");\n}',
                    language: 'rust'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should highlight SQL code', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'SELECT * FROM users WHERE id = 1;',
                    language: 'sql'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Theme Support', () => {
        it('should use github-dark theme by default', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'const x = 1;',
                    language: 'javascript'
                })
                .expect(200);

            expect(res.body.theme).toBe('github-dark');
        });

        it('should support github-light theme', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'const x = 1;',
                    language: 'javascript',
                    theme: 'github-light'
                })
                .expect(200);

            expect(res.body.theme).toBe('github-light');
        });

        it('should support dracula theme', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'const x = 1;',
                    language: 'javascript',
                    theme: 'dracula'
                })
                .expect(200);

            expect(res.body.theme).toBe('dracula');
        });
    });

    describe('Error Handling', () => {
        it('should return 400 when code field is missing', async () => {
            const res = await api()
                .post('/render/code')
                .send({ language: 'javascript' })
                .expect(400);

            expect(res.body.success).toBe(false);
            expect(res.body.error).toContain('code');
        });

        it('should use fallback for unsupported languages', async () => {
            const res = await api()
                .post('/render/code')
                .send({
                    code: 'some code',
                    language: 'unknown-lang'
                });

            // Should return success with fallback or regular HTML
            expect(res.body.success).toBe(true);
            expect(res.body.html).toBeDefined();
        });
    });
});
