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
    { id: "100", label: "Level 100" },
    { id: "200", label: "Level 200" },
    { id: "300", label: "Level 300" },
    { id: "400", label: "Level 400" },
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
    { id: "friend", label: "Through a friend" },
    { id: "whatsapp", label: "WhatsApp" },
    { id: "twitter", label: "Twitter / X" },
    { id: "instagram", label: "Instagram" },
    { id: "lecturer", label: "Lecturer or TA" },
    { id: "search", label: "Google search" },
    { id: "other", label: "Other" },
] as const;

export const features = [
    {
        id: "university-compliant",
        title: "University Compliant",
        description: "Built with Ghanaian university formatting standards in mind. Your lecturers will approve.",
        highlight: true,
    },
    {
        id: "british-english",
        title: "No More US Spelling Marks",
        description: '"Colour" not "color", "organisation" not "organization". Never lose marks again.',
    },
    {
        id: "references",
        title: "Proper References",
        description: "APA, Harvard, IEEE — citations formatted exactly how your lecturers want them.",
    },
    {
        id: "real-citations",
        title: "Real Citations",
        description: "We find actual academic papers with DOIs. No fake references, no hallucinations.",
    },
    {
        id: "equations",
        title: "Perfect Equations",
        description: "Complex LaTeX math rendered beautifully. From thermodynamics to quantum mechanics.",
    },
    {
        id: "diagrams",
        title: "Smart Diagrams",
        description: "Flowcharts, process diagrams, geological maps — describe it, we create it.",
    },
] as const;

// Problems - Before/After comparisons
export const problems = [
    {
        before: {
            text: '"Color" on your slides',
            subtext: 'US spelling = marks lost',
        },
        after: {
            text: '"Colour" automatically',
            subtext: 'British English throughout',
        },
    },
    {
        before: {
            text: 'Manually hunting for citations',
            subtext: 'At 2 AM before deadline',
        },
        after: {
            text: 'Real DOI-verified papers',
            subtext: 'APA, Harvard, IEEE ready',
        },
    },
    {
        before: {
            text: '"50kg" in your equations',
            subtext: 'SI unit formatting wrong',
        },
        after: {
            text: '"50 kg" done right',
            subtext: 'Proper spacing & symbols',
        },
    },
    {
        before: {
            text: 'Hours on formatting',
            subtext: 'Instead of studying',
        },
        after: {
            text: 'Minutes to completion',
            subtext: 'More time for what matters',
        },
    },
] as const;

// FAQs
export const faqs = [
    {
        question: "Is the beta free?",
        answer: "Yes! Beta testers get free access. We may introduce pricing later, but beta testers will get special deals.",
    },
    {
        question: "When will I get access?",
        answer: "We're rolling out access in batches. Sign up now and you'll receive an email when your spot is ready.",
    },
    {
        question: "What can I use it for?",
        answer: "Class presentations, seminars, group projects, term papers — any academic presentation you need.",
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
