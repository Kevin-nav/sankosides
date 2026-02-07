/**
 * Seed Templates, Themes, and Palettes to Convex
 * 
 * This script reads the exported template data from Neon and seeds it into Convex.
 * 
 * Usage:
 *   cd sanko-frontend
 *   npx tsx scripts/seed-templates.ts
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

async function seedTemplates() {
    console.log("🔗 Connecting to Convex...");
    const client = new ConvexHttpClient(CONVEX_URL!);

    // Read the exported data
    const dataPath = path.resolve(__dirname, "../../sanko-backend/templates_export.json");
    console.log(`📁 Reading data from: ${dataPath}`);

    if (!fs.existsSync(dataPath)) {
        console.error("ERROR: templates_export.json not found. Run the export script first.");
        process.exit(1);
    }

    const rawData = fs.readFileSync(dataPath, "utf-8");
    const data = JSON.parse(rawData);

    console.log(`📊 Found data to seed:`);
    console.log(`   - Templates: ${data.templates.length}`);
    console.log(`   - Palettes: ${data.palettes.length}`);
    console.log(`   - Themes: ${data.themes.length}`);

    // Convert null values to undefined for Convex compatibility
    const cleanTemplates = data.templates.map((t: any) => ({
        ...t,
        description: t.description ?? undefined,
        cssStyles: t.cssStyles ?? undefined,
    }));

    const cleanThemes = data.themes.map((t: any) => ({
        ...t,
        description: t.description ?? undefined,
        cssOverrides: t.cssOverrides ?? undefined,
        layoutStyle: t.layoutStyle ?? undefined,
    }));

    // Call the Convex mutation to seed the data
    try {
        const result = await client.mutation(api.templates.seedTemplateData, {
            templates: cleanTemplates,
            palettes: data.palettes,
            themes: cleanThemes,
        });

        console.log("\n✅ Seeding complete!");
        console.log(`   Templates: ${result.counts.templates}`);
        console.log(`   Palettes: ${result.counts.palettes}`);
        console.log(`   Themes: ${result.counts.themes}`);
    } catch (error) {
        console.error("ERROR: Failed to seed data:", error);
        process.exit(1);
    }
}

seedTemplates();
