import { pgTable, text, timestamp, uuid, varchar } from 'drizzle-orm/pg-core';

export const betaSignups = pgTable('beta_signups', {
    id: uuid('id').defaultRandom().primaryKey(),

    // Contact Info (Step 1)
    fullName: varchar('full_name', { length: 255 }).notNull(),
    email: varchar('email', { length: 255 }).notNull().unique(),
    whatsapp: varchar('whatsapp', { length: 50 }),

    // University Info (Step 2)
    university: varchar('university', { length: 100 }).notNull(),
    campus: varchar('campus', { length: 100 }),
    otherUniversity: varchar('other_university', { length: 255 }),
    academicLevel: varchar('academic_level', { length: 50 }).notNull(),
    department: varchar('department', { length: 255 }),

    // Preferences (Step 3)
    frequency: varchar('frequency', { length: 50 }),
    tools: text('tools'),  // JSON array stored as text
    painPoints: text('pain_points'),
    expectations: text('expectations'),
    referral: varchar('referral', { length: 100 }),

    // Metadata
    createdAt: timestamp('created_at').defaultNow(),
    ipAddress: varchar('ip_address', { length: 45 }),
    emailSentAt: timestamp('email_sent_at'),  // Track when welcome email was sent
});

export type BetaSignup = typeof betaSignups.$inferSelect;
export type NewBetaSignup = typeof betaSignups.$inferInsert;
