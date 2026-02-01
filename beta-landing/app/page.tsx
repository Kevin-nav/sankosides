"use client";

import { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { Hero } from '@/components/Hero';
import { ProblemSection } from '@/components/ProblemSection';
import { FeaturesSection } from '@/components/FeaturesSection';
import { HowItWorks } from '@/components/HowItWorks';
import { FAQSection } from '@/components/FAQSection';
import { Footer } from '@/components/Footer';
import { BetaSignupForm } from '@/components/BetaSignupForm';

export default function Home() {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [prefilledEmail, setPrefilledEmail] = useState('');

  const openForm = (email?: string) => {
    if (email) setPrefilledEmail(email);
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    // Optional: clear email after close if desired, but keeping it might be better UX if they re-open
  };

  return (
    <main className="min-h-screen bg-[#0a0a0f]">
      <Navbar onCtaClick={() => openForm()} />
      <Hero onCtaClick={openForm} />
      <ProblemSection />
      <FeaturesSection />
      <HowItWorks onCtaClick={() => openForm()} />
      <FAQSection />
      <Footer />

      <BetaSignupForm isOpen={isFormOpen} onClose={closeForm} initialEmail={prefilledEmail} />
    </main>
  );
}
