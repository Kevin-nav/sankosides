import { useState, useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { ProblemSection } from './components/ProblemSection';
import { FeaturesSection } from './components/FeaturesSection';
import { HowItWorks } from './components/HowItWorks';
import { FAQSection } from './components/FAQSection';
import { Footer } from './components/Footer';
import { BetaSignupForm } from './components/BetaSignupForm';

// Register GSAP plugins
gsap.registerPlugin(ScrollTrigger);

function App() {
  const [isFormOpen, setIsFormOpen] = useState(false);

  // Smooth scroll reset on mount
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  // Lock body scroll when form is open
  useEffect(() => {
    if (isFormOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isFormOpen]);

  const openForm = () => {
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
  };

  return (
    <div className="min-h-screen bg-neutral-950">
      <Navbar onCtaClick={openForm} />

      <main>
        <Hero onCtaClick={openForm} />
        <ProblemSection />
        <FeaturesSection />
        <HowItWorks onCtaClick={openForm} />
        <FAQSection />
      </main>

      <Footer />

      {/* Beta Signup Modal */}
      <BetaSignupForm isOpen={isFormOpen} onClose={closeForm} />
    </div>
  );
}

export default App;
