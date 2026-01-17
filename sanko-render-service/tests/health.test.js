/**
 * Health Endpoint Tests
 */
const { api } = require('./setup');

describe('GET /health', () => {
    it('should return health status with all required fields', async () => {
        const res = await api()
            .get('/health')
            .expect(200);

        expect(res.body).toHaveProperty('status', 'ok');
        expect(res.body).toHaveProperty('service', 'sanko-render-service');
        expect(res.body).toHaveProperty('uptime');
        expect(res.body).toHaveProperty('requests_processed');
        expect(res.body).toHaveProperty('mermaid_ready');
        expect(res.body).toHaveProperty('chrome_path');
    });
});
