import { useState, useRef, useEffect, forwardRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { gsap } from 'gsap';
import { X, ArrowRight, ArrowLeft, Loader2, CheckCircle, Sparkles } from 'lucide-react';
import {
    universities,
    academicLevels,
    presentationFrequency,
    currentTools,
    referralSources,
} from '../data/constants';

interface BetaSignupFormProps {
    isOpen: boolean;
    onClose: () => void;
}

interface FormData {
    fullName: string;
    email: string;
    whatsapp: string;
    university: string;
    campus: string;
    otherUniversity: string;
    academicLevel: string;
    department: string;
    frequency: string;
    painPoints: string;
    tools: string[];
    expectations: string;
    referral: string;
}

const initialFormData: FormData = {
    fullName: '',
    email: '',
    whatsapp: '',
    university: '',
    campus: '',
    otherUniversity: '',
    academicLevel: '',
    department: '',
    frequency: '',
    painPoints: '',
    tools: [],
    expectations: '',
    referral: '',
};

export const BetaSignupForm = forwardRef<HTMLDivElement, BetaSignupFormProps>(
    ({ isOpen, onClose }, _ref) => {
        const [step, setStep] = useState(1);
        const [formData, setFormData] = useState<FormData>(initialFormData);
        const [isSubmitting, setIsSubmitting] = useState(false);
        const [isSuccess, setIsSuccess] = useState(false);
        const [error, setError] = useState('');
        const formRef = useRef<HTMLDivElement>(null);

        const totalSteps = 3;
        const selectedUniversity = universities.find((u) => u.id === formData.university);
        const showCampus = selectedUniversity && 'hasCampuses' in selectedUniversity && selectedUniversity.hasCampuses;
        const campusList = selectedUniversity && 'campuses' in selectedUniversity ? selectedUniversity.campuses : [];
        const showOtherInput = formData.university === 'other';

        // Reset form when opened
        useEffect(() => {
            if (isOpen) {
                setStep(1);
                setFormData(initialFormData);
                setIsSuccess(false);
                setError('');
            }
        }, [isOpen]);

        // Entrance animation for form content
        useEffect(() => {
            if (formRef.current && isOpen) {
                gsap.fromTo(
                    formRef.current,
                    { opacity: 0, y: 20 },
                    { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }
                );
            }
        }, [isOpen]);

        const updateField = (field: keyof FormData, value: string | string[]) => {
            setFormData((prev) => ({ ...prev, [field]: value }));
        };

        const toggleTool = (toolId: string) => {
            setFormData((prev) => ({
                ...prev,
                tools: prev.tools.includes(toolId)
                    ? prev.tools.filter((t) => t !== toolId)
                    : [...prev.tools, toolId],
            }));
        };

        const canProceed = () => {
            switch (step) {
                case 1:
                    return formData.fullName.trim() !== '' && formData.email.includes('@');
                case 2:
                    const hasUniversity =
                        formData.university !== '' &&
                        (formData.university !== 'other' || formData.otherUniversity.trim() !== '');
                    const hasCampus = !showCampus || formData.campus !== '';
                    return hasUniversity && hasCampus && formData.academicLevel !== '';
                case 3:
                    return true; // Optional step
                default:
                    return false;
            }
        };

        const handleNext = () => {
            if (step < totalSteps) {
                setStep(step + 1);
            }
        };

        const handleBack = () => {
            if (step > 1) {
                setStep(step - 1);
            }
        };

        const handleSubmit = async () => {
            setIsSubmitting(true);
            setError('');

            try {
                // For now, just simulate API call
                // In production, this would POST to /api/beta-signup
                await new Promise((resolve) => setTimeout(resolve, 1500));

                // Store in localStorage as backup
                const signups = JSON.parse(localStorage.getItem('beta_signups') || '[]');
                signups.push({ ...formData, timestamp: new Date().toISOString() });
                localStorage.setItem('beta_signups', JSON.stringify(signups));

                setIsSuccess(true);
            } catch (err) {
                setError('Something went wrong. Please try again.');
            } finally {
                setIsSubmitting(false);
            }
        };

        const slideVariants = {
            enter: (direction: number) => ({
                x: direction > 0 ? 50 : -50,
                opacity: 0,
            }),
            center: {
                x: 0,
                opacity: 1,
            },
            exit: (direction: number) => ({
                x: direction < 0 ? 50 : -50,
                opacity: 0,
            }),
        };

        return (
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
                        onClick={(e) => e.target === e.currentTarget && onClose()}
                    >
                        <motion.div
                            ref={formRef}
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                            className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl"
                        >
                            {/* Close button */}
                            <button
                                onClick={onClose}
                                className="absolute top-4 right-4 p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors z-10"
                            >
                                <X className="w-5 h-5" />
                            </button>

                            {/* Success State */}
                            {isSuccess ? (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="p-8 text-center"
                                >
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ type: 'spring', delay: 0.2 }}
                                        className="w-20 h-20 mx-auto mb-6 rounded-full bg-emerald-500/20 flex items-center justify-center"
                                    >
                                        <CheckCircle className="w-10 h-10 text-emerald-400" />
                                    </motion.div>
                                    <h3 className="text-2xl font-bold text-white mb-3">You're on the list! 🎉</h3>
                                    <p className="text-neutral-400 mb-6">
                                        We'll send you an email when your beta access is ready.
                                        {formData.university === 'umat' && ' UMaT students get priority!'}
                                    </p>
                                    <button onClick={onClose} className="btn btn-primary">
                                        Got it
                                    </button>
                                </motion.div>
                            ) : (
                                <>
                                    {/* Header */}
                                    <div className="p-6 pb-4 border-b border-neutral-800">
                                        <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium mb-2">
                                            <Sparkles className="w-4 h-4" />
                                            <span>Free Beta Access</span>
                                        </div>
                                        <h2 className="text-xl font-bold text-white">Join the Beta</h2>

                                        {/* Progress bar */}
                                        <div className="mt-4 flex gap-2">
                                            {[1, 2, 3].map((s) => (
                                                <div
                                                    key={s}
                                                    className={`h-1 flex-1 rounded-full transition-colors duration-300 ${s <= step ? 'bg-emerald-500' : 'bg-neutral-700'
                                                        }`}
                                                />
                                            ))}
                                        </div>
                                        <p className="text-xs text-neutral-500 mt-2">
                                            Step {step} of {totalSteps}
                                        </p>
                                    </div>

                                    {/* Form Content */}
                                    <div className="p-6">
                                        <AnimatePresence mode="wait" custom={step}>
                                            <motion.div
                                                key={step}
                                                custom={step}
                                                variants={slideVariants}
                                                initial="enter"
                                                animate="center"
                                                exit="exit"
                                                transition={{ duration: 0.3 }}
                                            >
                                                {step === 1 && (
                                                    <div className="space-y-4">
                                                        <h3 className="text-lg font-semibold text-white mb-4">
                                                            Let's start with your contact info
                                                        </h3>

                                                        <div>
                                                            <label className="label">Full Name *</label>
                                                            <input
                                                                type="text"
                                                                className="input"
                                                                placeholder="e.g. Kofi Mensah"
                                                                value={formData.fullName}
                                                                onChange={(e) => updateField('fullName', e.target.value)}
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="label">Email Address *</label>
                                                            <input
                                                                type="email"
                                                                className="input"
                                                                placeholder="your.email@example.com"
                                                                value={formData.email}
                                                                onChange={(e) => updateField('email', e.target.value)}
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="label">
                                                                WhatsApp Number{' '}
                                                                <span className="text-neutral-500">(optional)</span>
                                                            </label>
                                                            <input
                                                                type="tel"
                                                                className="input"
                                                                placeholder="+233 XX XXX XXXX"
                                                                value={formData.whatsapp}
                                                                onChange={(e) => updateField('whatsapp', e.target.value)}
                                                            />
                                                        </div>
                                                    </div>
                                                )}

                                                {step === 2 && (
                                                    <div className="space-y-4">
                                                        <h3 className="text-lg font-semibold text-white mb-4">
                                                            Tell us about your studies
                                                        </h3>

                                                        <div>
                                                            <label className="label">University *</label>
                                                            <select
                                                                className="select"
                                                                value={formData.university}
                                                                onChange={(e) => {
                                                                    updateField('university', e.target.value);
                                                                    updateField('campus', '');
                                                                }}
                                                            >
                                                                <option value="">Select your university</option>
                                                                {universities.map((uni) => (
                                                                    <option key={uni.id} value={uni.id}>
                                                                        {uni.name}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </div>

                                                        {showCampus && (
                                                            <motion.div
                                                                initial={{ opacity: 0, height: 0 }}
                                                                animate={{ opacity: 1, height: 'auto' }}
                                                                exit={{ opacity: 0, height: 0 }}
                                                            >
                                                                <label className="label">Campus *</label>
                                                                <select
                                                                    className="select"
                                                                    value={formData.campus}
                                                                    onChange={(e) => updateField('campus', e.target.value)}
                                                                >
                                                                    <option value="">Select campus</option>
                                                                    {campusList.map((campus: string) => (
                                                                        <option key={campus} value={campus}>
                                                                            {campus}
                                                                        </option>
                                                                    ))}
                                                                </select>
                                                            </motion.div>
                                                        )}

                                                        {showOtherInput && (
                                                            <motion.div
                                                                initial={{ opacity: 0, height: 0 }}
                                                                animate={{ opacity: 1, height: 'auto' }}
                                                                exit={{ opacity: 0, height: 0 }}
                                                            >
                                                                <label className="label">University Name *</label>
                                                                <input
                                                                    type="text"
                                                                    className="input"
                                                                    placeholder="Enter your university name"
                                                                    value={formData.otherUniversity}
                                                                    onChange={(e) =>
                                                                        updateField('otherUniversity', e.target.value)
                                                                    }
                                                                />
                                                            </motion.div>
                                                        )}

                                                        <div>
                                                            <label className="label">Academic Level *</label>
                                                            <select
                                                                className="select"
                                                                value={formData.academicLevel}
                                                                onChange={(e) => updateField('academicLevel', e.target.value)}
                                                            >
                                                                <option value="">Select your level</option>
                                                                {academicLevels.map((level) => (
                                                                    <option key={level.id} value={level.id}>
                                                                        {level.label}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </div>

                                                        <div>
                                                            <label className="label">
                                                                Department / Programme{' '}
                                                                <span className="text-neutral-500">(optional)</span>
                                                            </label>
                                                            <input
                                                                type="text"
                                                                className="input"
                                                                placeholder="e.g. Mining Engineering"
                                                                value={formData.department}
                                                                onChange={(e) => updateField('department', e.target.value)}
                                                            />
                                                        </div>
                                                    </div>
                                                )}

                                                {step === 3 && (
                                                    <div className="space-y-4">
                                                        <h3 className="text-lg font-semibold text-white mb-4">
                                                            Help us build what you need
                                                        </h3>

                                                        <div>
                                                            <label className="label">
                                                                How often do you make presentations?
                                                            </label>
                                                            <div className="radio-group">
                                                                {presentationFrequency.map((freq) => (
                                                                    <label key={freq.id} className="radio-label">
                                                                        <input
                                                                            type="radio"
                                                                            name="frequency"
                                                                            checked={formData.frequency === freq.id}
                                                                            onChange={() => updateField('frequency', freq.id)}
                                                                        />
                                                                        {freq.label}
                                                                    </label>
                                                                ))}
                                                            </div>
                                                        </div>

                                                        <div>
                                                            <label className="label">
                                                                What tools do you currently use?
                                                            </label>
                                                            <div className="checkbox-group">
                                                                {currentTools.map((tool) => (
                                                                    <label key={tool.id} className="checkbox-label">
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={formData.tools.includes(tool.id)}
                                                                            onChange={() => toggleTool(tool.id)}
                                                                        />
                                                                        {tool.label}
                                                                    </label>
                                                                ))}
                                                            </div>
                                                        </div>

                                                        <div>
                                                            <label className="label">
                                                                What frustrates you most about making slides?
                                                            </label>
                                                            <textarea
                                                                className="textarea"
                                                                placeholder="e.g. Formatting citations takes forever..."
                                                                value={formData.painPoints}
                                                                onChange={(e) => updateField('painPoints', e.target.value)}
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="label">
                                                                What would make this tool a must-have for you?
                                                            </label>
                                                            <textarea
                                                                className="textarea"
                                                                placeholder="What features do you expect?"
                                                                value={formData.expectations}
                                                                onChange={(e) => updateField('expectations', e.target.value)}
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="label">How did you hear about us?</label>
                                                            <select
                                                                className="select"
                                                                value={formData.referral}
                                                                onChange={(e) => updateField('referral', e.target.value)}
                                                            >
                                                                <option value="">Select an option</option>
                                                                {referralSources.map((source) => (
                                                                    <option key={source.id} value={source.id}>
                                                                        {source.label}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </div>
                                                    </div>
                                                )}
                                            </motion.div>
                                        </AnimatePresence>

                                        {/* Error message */}
                                        {error && (
                                            <p className="text-red-400 text-sm mt-4">{error}</p>
                                        )}

                                        {/* Navigation buttons */}
                                        <div className="flex gap-3 mt-6">
                                            {step > 1 && (
                                                <button
                                                    onClick={handleBack}
                                                    className="flex-1 py-3 px-4 rounded-xl border border-neutral-700 text-neutral-300 hover:bg-neutral-800 transition-colors flex items-center justify-center gap-2"
                                                >
                                                    <ArrowLeft className="w-4 h-4" />
                                                    Back
                                                </button>
                                            )}

                                            {step < totalSteps ? (
                                                <button
                                                    onClick={handleNext}
                                                    disabled={!canProceed()}
                                                    className={`flex-1 py-3 px-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-all ${canProceed()
                                                        ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                                                        : 'bg-neutral-700 text-neutral-400 cursor-not-allowed'
                                                        }`}
                                                >
                                                    Next
                                                    <ArrowRight className="w-4 h-4" />
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={handleSubmit}
                                                    disabled={isSubmitting}
                                                    className="flex-1 py-3 px-4 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors flex items-center justify-center gap-2"
                                                >
                                                    {isSubmitting ? (
                                                        <>
                                                            <Loader2 className="w-4 h-4 animate-spin" />
                                                            Submitting...
                                                        </>
                                                    ) : (
                                                        <>
                                                            Join the Beta
                                                            <Sparkles className="w-4 h-4" />
                                                        </>
                                                    )}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </>
                            )}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        );
    }
);

BetaSignupForm.displayName = 'BetaSignupForm';
