'use client';

import { useState, useRef, useEffect } from 'react';
import { gsap } from 'gsap';
import { Check, ChevronRight, Loader2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';

interface SurveyData {
    email: string;
    operatingSystem: string;
    browser: string;
    citationStyle: string;
    contentSource: string;
    visualStyle: string;
}

const CITATION_EXAMPLES: Record<string, string> = {
    "APA": "(Smith, 2023)",
    "MLA": "(Smith 42)",
    "Harvard": "(Smith 2023, p. 42)",
    "IEEE": "[1]",
    "Chicago": "Smith, *Title*, 42.",
    "I don't even know 😭": "🤷‍♂️"
};

const QUESTIONS = [
    {
        id: 'operatingSystem',
        question: "Which specific Operating System do you use most?",
        options: ["Windows", "macOS", "Linux", "iPadOS / Tablet", "ChromeOS"],
        type: 'select'
    },
    {
        id: 'browser',
        question: "Which browser is your daily driver?",
        options: ["Chrome", "Edge", "Safari", "Firefox", "Arc / Other"],
        type: 'select'
    },
    {
        id: 'citationStyle',
        question: "Which citation style do you normally use?",
        options: ["APA", "MLA", "Harvard", "IEEE", "Chicago", "I don't even know 😭"],
        type: 'select-with-example'
    },
    {
        id: 'contentSource',
        question: "Where does your slide content usually come from?",
        options: [
            "PDF Textbooks / Papers",
            "My own lecture notes (Word/Notion)",
            "Wikipedia / Online Research",
            "I use ChatGPT to generate it"
        ],
        type: 'select'
    },
    {
        id: 'visualStyle',
        question: "If you had to pick one visual aesthetic:",
        options: [
            "Minimal & Clean (Apple style)",
            "Data-Heavy & Dense (Research style)",
            "Vibrant & Creative (Pitch deck)"
        ],
        type: 'select'
    }
];

export default function SurveyFlow() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const emailParam = searchParams.get('email');

    // Auto-fill email if present, otherwise ask for it
    const [currentStep, setCurrentStep] = useState(emailParam ? 0 : -1);
    const [data, setData] = useState<Partial<SurveyData>>({
        email: emailParam || '',
    });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [priorityPos, setPriorityPos] = useState<number | null>(null);

    const containerRef = useRef<HTMLDivElement>(null);
    const questionRef = useRef<HTMLDivElement>(null);

    // Animation helper
    const animateTransition = (callback: () => void) => {
        if (!questionRef.current) return callback();

        const tl = gsap.timeline();

        tl.to(questionRef.current, {
            y: -20,
            opacity: 0,
            duration: 0.3,
            ease: "power2.in",
            onComplete: () => {
                callback();
                gsap.set(questionRef.current, { y: 20, opacity: 0 });
                gsap.to(questionRef.current, {
                    y: 0,
                    opacity: 1,
                    duration: 0.4,
                    ease: "power2.out"
                });
            }
        });
    };

    const handleNext = (value: string) => {
        const field = currentStep === -1 ? 'email' : QUESTIONS[currentStep].id;

        setData(prev => ({ ...prev, [field]: value }));

        if (currentStep < QUESTIONS.length - 1) {
            animateTransition(() => setCurrentStep(prev => prev + 1));
        } else {
            submitSurvey({ ...data, [field]: value } as SurveyData);
        }
    };

    const submitSurvey = async (finalData: SurveyData) => {
        setIsSubmitting(true);
        try {
            const res = await fetch('/api/survey', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalData),
            });

            const result = await res.json();
            if (result.success) {
                setPriorityPos(result.priorityPosition);
                // Animation for success state
                gsap.to(containerRef.current, {
                    scale: 0.95,
                    opacity: 0,
                    duration: 0.3,
                    onComplete: () => {
                        setCurrentStep(999); // Success state
                        gsap.set(containerRef.current, { scale: 1, opacity: 0 });
                        gsap.to(containerRef.current, { scale: 1, opacity: 1, duration: 0.5 });
                    }
                });
            }
        } catch (error) {
            console.error(error);
            alert("Something went wrong. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    // Render Logic
    if (priorityPos !== null) {
        return (
            <div ref={containerRef} className="max-w-md w-full mx-auto text-center p-8">
                <div className="mb-6 flex justify-center">
                    <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center border border-green-500/20">
                        <Check className="w-10 h-10 text-green-500" />
                    </div>
                </div>
                <h2 className="text-3xl font-bold text-white mb-4">You're all set!</h2>
                <p className="text-zinc-400 mb-8">
                    Your profile is complete. You've bumped up your spot on the waitlist.
                </p>

                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-8 relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <p className="text-sm text-zinc-500 uppercase tracking-wider font-medium mb-1">Current Priority Position</p>
                    <p className="text-4xl font-mono font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-blue-500">
                        #{priorityPos}
                    </p>
                </div>

                <button
                    onClick={() => router.push('/')}
                    className="text-zinc-500 hover:text-white transition-colors text-sm"
                >
                    Back to Home
                </button>
            </div>
        );
    }

    const currentQuestion = currentStep === -1
        ? { id: 'email', question: "First, confirming your email", placeholder: "your@email.com", type: 'email' }
        : QUESTIONS[currentStep];

    const progress = ((currentStep + 1) / QUESTIONS.length) * 100;

    return (
        <div className="w-full max-w-xl mx-auto p-6" ref={containerRef}>
            {/* Progress Bar */}
            <div className="w-full h-1 bg-zinc-800 rounded-full mb-12 overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-blue-500 transition-all duration-500"
                    style={{ width: `${currentStep === -1 ? 5 : progress}%` }}
                />
            </div>

            <div ref={questionRef} className="min-h-[300px] flex flex-col justify-center">
                <h2 className="text-2xl md:text-3xl font-bold text-white mb-8 leading-tight">
                    {currentQuestion.question}
                </h2>

                <div className="space-y-4">
                    {(currentQuestion.type === 'text' || currentQuestion.type === 'email') && (
                        <InputForm
                            key={currentQuestion.id}
                            type={currentQuestion.type}
                            placeholder={currentQuestion.placeholder}
                            onSubmit={handleNext}
                        />
                    )}

                    {currentQuestion.type === 'textarea' && (
                        <TextAreaForm
                            key={currentQuestion.id}
                            placeholder={currentQuestion.placeholder}
                            onSubmit={handleNext}
                            isSubmitting={isSubmitting}
                        />
                    )}

                    {(currentQuestion.type === 'select' || currentQuestion.type === 'select-with-example') && 'options' in currentQuestion && (
                        <div className="grid gap-3">
                            {currentQuestion.options?.map((opt) => (
                                <button
                                    key={opt}
                                    onClick={() => handleNext(opt)}
                                    className="w-full text-left p-4 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-300 hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all group flex items-center justify-between"
                                >
                                    <span>{opt}</span>
                                    {currentQuestion.type === 'select-with-example' && CITATION_EXAMPLES[opt] && (
                                        <span className="text-zinc-500 text-sm italic ml-2">
                                            {CITATION_EXAMPLES[opt]}
                                        </span>
                                    )}
                                    <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity text-emerald-500 ml-auto" />
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// Sub-components for inputs to handle "Enter" key logic cleanly
function InputForm({ type, placeholder, onSubmit }: { type: string, placeholder?: string, onSubmit: (v: string) => void }) {
    const [val, setVal] = useState('');
    return (
        <form onSubmit={(e) => { e.preventDefault(); if (val) onSubmit(val); }}>
            <div className="relative">
                <input
                    type={type}
                    value={val}
                    onChange={(e) => setVal(e.target.value)}
                    placeholder={placeholder}
                    className="w-full bg-transparent border-b-2 border-zinc-800 focus:border-emerald-500 py-4 text-xl text-white placeholder-zinc-600 outline-none transition-colors"
                    autoFocus
                />
                <button
                    type="submit"
                    disabled={!val}
                    className="absolute right-0 top-1/2 -translate-y-1/2 p-2 text-zinc-400 hover:text-emerald-400 disabled:opacity-0 transition-all"
                >
                    <ChevronRight className="w-6 h-6" />
                </button>
            </div>
        </form>
    );
}

function TextAreaForm({ placeholder, onSubmit, isSubmitting }: { placeholder?: string, onSubmit: (v: string) => void, isSubmitting: boolean }) {
    const [val, setVal] = useState('');
    return (
        <div className="space-y-6">
            <textarea
                value={val}
                onChange={(e) => setVal(e.target.value)}
                placeholder={placeholder}
                className="w-full bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 text-lg text-white placeholder-zinc-600 outline-none focus:border-emerald-500/50 transition-colors min-h-[120px] resize-none"
                autoFocus
            />
            <button
                onClick={() => val && onSubmit(val)}
                disabled={!val || isSubmitting}
                className="bg-white text-black font-semibold py-3 px-6 rounded-lg hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                {isSubmitting ? 'Finishing...' : 'Submit'}
            </button>
        </div>
    );
}
