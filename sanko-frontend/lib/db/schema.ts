import { pgTable, text, timestamp, uuid, jsonb } from "drizzle-orm/pg-core";

// Users table - linked to Firebase Auth UID
export const users = pgTable("users", {
    id: uuid("id").primaryKey().defaultRandom(),
    firebaseUid: text("firebase_uid").notNull().unique(),
    email: text("email").notNull(),
    displayName: text("display_name"),
    photoUrl: text("photo_url"),
    universityProfile: jsonb("university_profile"), // { name, department, logo, colors }
    preferences: jsonb("preferences"), // { theme, citationStyle, language, marketingEmails }
    subscriptionTier: text("subscription_tier").default("free"), // free, pro
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Projects table - slide generation projects
export const projects = pgTable("projects", {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
        .notNull()
        .references(() => users.id, { onDelete: "cascade" }),
    title: text("title").notNull(),
    description: text("description"),
    thumbnailUrl: text("thumbnail_url"),
    status: text("status").default("draft"), // draft, negotiating, generating, completed
    sessionId: uuid("session_id"), // Reference to playground_sessions
    slidesData: jsonb("slides_data"), // Generated slides data
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// TypeScript types inferred from schema
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type Project = typeof projects.$inferSelect;
export type NewProject = typeof projects.$inferInsert;
