import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

// =============================================================================
// Universities
// =============================================================================

export const listUniversities = query({
    handler: async (ctx) => {
        return await ctx.db.query("universities").collect();
    },
});

export const getUniversity = query({
    args: { universityId: v.string() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("universities")
            .withIndex("by_university_id", (q) => q.eq("universityId", args.universityId))
            .first();
    },
});

export const createUniversity = mutation({
    args: {
        universityId: v.string(),
        name: v.string(),
        shortName: v.string(),
        country: v.string(),
        defaultCitationStyle: v.string(),
        spellingVariant: v.string(),
        unitSystem: v.string(),
    },
    handler: async (ctx, args) => {
        const now = Date.now();
        return await ctx.db.insert("universities", {
            ...args,
            createdAt: now,
            updatedAt: now,
        });
    },
});

// =============================================================================
// Faculties
// =============================================================================

export const getFacultiesByUniversity = query({
    args: { universityId: v.id("universities") },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("faculties")
            .withIndex("by_university", (q) => q.eq("universityId", args.universityId))
            .collect();
    },
});

export const createFaculty = mutation({
    args: {
        universityId: v.id("universities"),
        facultyId: v.string(),
        name: v.string(),
        shortName: v.string(),
    },
    handler: async (ctx, args) => {
        const now = Date.now();
        return await ctx.db.insert("faculties", {
            ...args,
            createdAt: now,
            updatedAt: now,
        });
    },
});

// =============================================================================
// Departments
// =============================================================================

export const getDepartmentsByFaculty = query({
    args: { facultyId: v.id("faculties") },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("departments")
            .withIndex("by_faculty", (q) => q.eq("facultyId", args.facultyId))
            .collect();
    },
});

export const createDepartment = mutation({
    args: {
        facultyId: v.id("faculties"),
        departmentId: v.string(),
        name: v.string(),
        isStem: v.boolean(),
    },
    handler: async (ctx, args) => {
        const now = Date.now();
        return await ctx.db.insert("departments", {
            ...args,
            createdAt: now,
            updatedAt: now,
        });
    },
});

// =============================================================================
// Full Hierarchy Query (replaces the backend /universities/hierarchy endpoint)
// =============================================================================

export const getFullHierarchy = query({
    handler: async (ctx) => {
        const universities = await ctx.db.query("universities").collect();

        const hierarchy = await Promise.all(
            universities.map(async (uni) => {
                const faculties = await ctx.db
                    .query("faculties")
                    .withIndex("by_university", (q) => q.eq("universityId", uni._id))
                    .collect();

                const facultiesWithDepts = await Promise.all(
                    faculties.map(async (fac) => {
                        const departments = await ctx.db
                            .query("departments")
                            .withIndex("by_faculty", (q) => q.eq("facultyId", fac._id))
                            .collect();

                        return {
                            facultyId: fac.facultyId,
                            name: fac.name,
                            shortName: fac.shortName,
                            departments: departments.map((dept) => ({
                                departmentId: dept.departmentId,
                                name: dept.name,
                                isStem: dept.isStem,
                            })),
                        };
                    })
                );

                return {
                    universityId: uni.universityId,
                    name: uni.name,
                    shortName: uni.shortName,
                    country: uni.country,
                    defaultCitationStyle: uni.defaultCitationStyle,
                    spellingVariant: uni.spellingVariant,
                    unitSystem: uni.unitSystem,
                    faculties: facultiesWithDepts,
                };
            })
        );

        return hierarchy;
    },
});

// =============================================================================
// Seed Data Mutation (for migrating data from Neon)
// =============================================================================

export const seedUniversityData = mutation({
    args: {
        universities: v.array(
            v.object({
                universityId: v.string(),
                name: v.string(),
                shortName: v.string(),
                country: v.string(),
                defaultCitationStyle: v.string(),
                spellingVariant: v.string(),
                unitSystem: v.string(),
                faculties: v.array(
                    v.object({
                        facultyId: v.string(),
                        name: v.string(),
                        shortName: v.string(),
                        departments: v.array(
                            v.object({
                                departmentId: v.string(),
                                name: v.string(),
                                isStem: v.boolean(),
                            })
                        ),
                    })
                ),
            })
        ),
    },
    handler: async (ctx, args) => {
        const now = Date.now();
        let uniCount = 0;
        let facCount = 0;
        let deptCount = 0;

        for (const uni of args.universities) {
            // Create university
            const uniId = await ctx.db.insert("universities", {
                universityId: uni.universityId,
                name: uni.name,
                shortName: uni.shortName,
                country: uni.country,
                defaultCitationStyle: uni.defaultCitationStyle,
                spellingVariant: uni.spellingVariant,
                unitSystem: uni.unitSystem,
                createdAt: now,
                updatedAt: now,
            });
            uniCount++;

            for (const fac of uni.faculties) {
                // Create faculty
                const facId = await ctx.db.insert("faculties", {
                    universityId: uniId,
                    facultyId: fac.facultyId,
                    name: fac.name,
                    shortName: fac.shortName,
                    createdAt: now,
                    updatedAt: now,
                });
                facCount++;

                for (const dept of fac.departments) {
                    // Create department
                    await ctx.db.insert("departments", {
                        facultyId: facId,
                        departmentId: dept.departmentId,
                        name: dept.name,
                        isStem: dept.isStem,
                        createdAt: now,
                        updatedAt: now,
                    });
                    deptCount++;
                }
            }
        }

        return {
            success: true,
            counts: {
                universities: uniCount,
                faculties: facCount,
                departments: deptCount,
            },
        };
    },
});
