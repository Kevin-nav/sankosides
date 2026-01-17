import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import * as schema from "./schema";

// Connection string from environment
const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
    throw new Error(
        "DATABASE_URL is not set. Please add your Neon connection string to .env.local"
    );
}

// Create the Neon SQL client
const sql = neon(connectionString);

// Create the Drizzle ORM instance with schema
export const db = drizzle(sql, { schema });

// Export schema for use in queries
export { schema };
