// University data for Ghana
export const universities = [
    {
        id: "umat",
        name: "University of Mines and Technology (UMaT)",
        hasCampuses: true,
        campuses: ["Tarkwa Campus (Main)", "Essikado Campus"],
        isPrimary: true,
    },
    { id: "knust", name: "Kwame Nkrumah University of Science and Technology (KNUST)" },
    { id: "ucc", name: "University of Cape Coast (UCC)" },
    { id: "ug", name: "University of Ghana (UG)" },
    { id: "uew", name: "University of Education, Winneba (UEW)" },
    { id: "uds", name: "University for Development Studies (UDS)" },
    { id: "gimpa", name: "Ghana Institute of Management and Public Administration (GIMPA)" },
    { id: "ashesi", name: "Ashesi University" },
    { id: "upsa", name: "University of Professional Studies (UPSA)" },
    { id: "ait", name: "Accra Institute of Technology (AIT)" },
    { id: "other", name: "Other (please specify)" },
] as const;

export const academicLevels = [
    { id: "100", label: "Level 100 (Freshman)" },
    { id: "200", label: "Level 200 (Sophomore)" },
    { id: "300", label: "Level 300 (Junior)" },
    { id: "400", label: "Level 400 (Senior)" },
    { id: "masters", label: "Postgraduate (Masters)" },
    { id: "phd", label: "Postgraduate (PhD)" },
    { id: "lecturer", label: "Lecturer / Teaching Assistant" },
] as const;

export const presentationFrequency = [
    { id: "weekly", label: "Weekly" },
    { id: "monthly", label: "Monthly" },
    { id: "semester", label: "A few times per semester" },
    { id: "rarely", label: "Rarely" },
] as const;

export const currentTools = [
    { id: "powerpoint", label: "Microsoft PowerPoint" },
    { id: "google-slides", label: "Google Slides" },
    { id: "canva", label: "Canva" },
    { id: "latex", label: "LaTeX / Beamer" },
    { id: "keynote", label: "Keynote" },
    { id: "none", label: "I don't make slides" },
] as const;

export const referralSources = [
    { id: "friend", label: "A friend or classmate" },
    { id: "whatsapp", label: "WhatsApp group" },
    { id: "twitter", label: "Twitter / X" },
    { id: "instagram", label: "Instagram" },
    { id: "lecturer", label: "Lecturer or TA" },
    { id: "search", label: "Google search" },
    { id: "other", label: "Other" },
] as const;

// Features - used for metadata and SEO
export const featuresList = [
    "UMaT Compliant formatting",
    "British English spelling",
    "Proper APA/Harvard/IEEE citations",
    "Real DOI-verified academic papers",
    "LaTeX equation rendering",
    "Smart diagram generation",
] as const;

export const faqs = [
    {
        question: "Is the beta free?",
        answer: "Yes! Beta testers get free access. We may introduce pricing later, but beta testers will get special deals.",
    },
    {
        question: "When will I get access?",
        answer: "We're rolling out access in batches. UMaT students get priority. You'll receive an email when your spot is ready.",
    },
    {
        question: "What can I use it for?",
        answer: "Class presentations, thesis defense, seminars, conference talks — any academic presentation you need.",
    },
    {
        question: "Will it work on my phone?",
        answer: "You can sign up and manage your account on mobile. The slide editor works best on a laptop or desktop.",
    },
    {
        question: "Is my data safe?",
        answer: "Absolutely. We don't share your documents or data. Your work stays private.",
    },
] as const;
