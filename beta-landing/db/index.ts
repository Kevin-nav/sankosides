import { neon, NeonQueryFunction } from '@neondatabase/serverless';
import { drizzle, NeonHttpDatabase } from 'drizzle-orm/neon-http';
import * as schema from './schema';

// Lazy initialization to avoid build-time errors when DATABASE_URL is not set
let dbInstance: NeonHttpDatabase<typeof schema> | null = null;

export function getDb(): NeonHttpDatabase<typeof schema> {
    if (!dbInstance) {
        if (!process.env.DATABASE_URL) {
            throw new Error('DATABASE_URL environment variable is not set');
        }
        const sql = neon(process.env.DATABASE_URL);
        dbInstance = drizzle(sql, { schema });
    }
    return dbInstance;
}

// For backward compatibility - but prefer using getDb() directly
export const db = new Proxy({} as NeonHttpDatabase<typeof schema>, {
    get(_, prop) {
        return (getDb() as unknown as Record<string | symbol, unknown>)[prop];
    },
});
