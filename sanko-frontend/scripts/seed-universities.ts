/**
 * Seed University Data to Convex
 * 
 * This script reads the exported university data from Neon and seeds it into Convex.
 * 
 * Usage:
 *   cd sanko-frontend
 *   npx tsx scripts/seed-universities.ts
 */

import * as dotenv from "dotenv";
import * as path from "path";

// Load environment variables from .env.local
dotenv.config({ path: path.resolve(__dirname, "../.env.local") });

import { ConvexHttpClient } from "convex/browser";
import { api } from "../convex/_generated/api";
import * as fs from "fs";

const CONVEX_URL = process.env.NEXT_PUBLIC_CONVEX_URL;

if (!CONVEX_URL) {
    console.error("ERROR: NEXT_PUBLIC_CONVEX_URL not set");
    process.exit(1);
}

async function seedUniversities() {
    console.log("🔗 Connecting to Convex...");
    const client = new ConvexHttpClient(CONVEX_URL!);

    // Read the exported data
    const dataPath = path.resolve(__dirname, "../../sanko-backend/universities_export.json");
    console.log(`📁 Reading data from: ${dataPath}`);

    if (!fs.existsSync(dataPath)) {
        console.error("ERROR: universities_export.json not found. Run the export script first.");
        process.exit(1);
    }

    const rawData = fs.readFileSync(dataPath, "utf-8");
    const data = JSON.parse(rawData);

    console.log(`📊 Found ${data.universities.length} universities to seed`);

    // Call the Convex mutation to seed the data
    try {
        const result = await client.mutation(api.universities.seedUniversityData, {
            universities: data.universities,
        });

        console.log("\n✅ Seeding complete!");
        console.log(`   Universities: ${result.counts.universities}`);
        console.log(`   Faculties: ${result.counts.faculties}`);
        console.log(`   Departments: ${result.counts.departments}`);
    } catch (error) {
        console.error("ERROR: Failed to seed data:", error);
        process.exit(1);
    }
}

seedUniversities();
