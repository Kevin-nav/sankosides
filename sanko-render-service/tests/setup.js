/**
 * Test Setup - Exports the Express app for Supertest
 * 
 * This file creates a testable version of the server that:
 * 1. Doesn't actually listen on a port (Supertest handles that)
 * 2. Exports the app instance for use in tests
 */

const request = require('supertest');

// We need to get the app from server.js
// For now, we'll make requests directly to the running server
// In a future refactor, we can export the app for in-process testing

const API_URL = process.env.TEST_API_URL || 'http://localhost:3001';

/**
 * Makes requests to the render service
 * @param {string} endpoint - The endpoint path (e.g., '/render/latex')
 * @returns {supertest.SuperTest}
 */
function api() {
    return request(API_URL);
}

module.exports = { api, API_URL };
