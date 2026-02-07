/**
 * Convex Hooks for University Data
 * 
 * Direct Convex queries for university hierarchy.
 * Replaces API calls to /universities endpoints.
 */

import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

// ===================================
// Types
// ===================================

export interface Department {
    _id: Id<"departments">;
    departmentId: string;
    name: string;
    isStem: boolean;
}

export interface Faculty {
    _id: Id<"faculties">;
    facultyId: string;
    name: string;
    shortName: string;
}

export interface University {
    _id: Id<"universities">;
    universityId: string;
    name: string;
    shortName: string;
    country: string;
    defaultCitationStyle: string;
    spellingVariant: string;
    unitSystem: string;
}

// ===================================
// Hooks - Direct Convex Queries
// ===================================

/**
 * Hook to fetch full university hierarchy
 * 
 * Returns all universities with their faculties and departments
 */
export function useUniversityHierarchy() {
    return useQuery(api.universities.getFullHierarchy);
}

/**
 * Hook to fetch list of universities (without nested data)
 */
export function useUniversities() {
    return useQuery(api.universities.listUniversities);
}

/**
 * Hook to fetch a single university by its string ID
 */
export function useUniversity(universityId: string | null) {
    return useQuery(
        api.universities.getUniversity,
        universityId ? { universityId } : "skip"
    );
}

/**
 * Hook to fetch faculties for a university
 * 
 * @param universityId - The Convex _id of the university (not the string universityId)
 */
export function useFaculties(universityId: Id<"universities"> | null) {
    return useQuery(
        api.universities.getFacultiesByUniversity,
        universityId ? { universityId } : "skip"
    );
}

/**
 * Hook to fetch departments for a faculty
 * 
 * @param facultyId - The Convex _id of the faculty (not the string facultyId)
 */
export function useDepartments(facultyId: Id<"faculties"> | null) {
    return useQuery(
        api.universities.getDepartmentsByFaculty,
        facultyId ? { facultyId } : "skip"
    );
}
