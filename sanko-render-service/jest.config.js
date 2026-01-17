/**
 * Jest configuration for sanko-render-service
 */
module.exports = {
    testEnvironment: 'node',
    testMatch: ['**/tests/**/*.test.js'],
    testTimeout: 30000, // 30s for browser-based tests
    verbose: true,
    // Don't run tests in parallel to avoid browser conflicts
    maxWorkers: 1,
};
