import React, { useState, useEffect, useCallback } from 'react';
import { SLIDES } from './data/slidesData';
import { SlideViewer } from './components/SlideViewer';
import { NavigationChrome } from './components/NavigationChrome';
import { SpeakerNotesPanel } from './components/SpeakerNotesPanel';
import { LightboxModal } from './components/LightboxModal';
import './styles/astryx.css';

export const App: React.FC = () => {
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [showNotes, setShowNotes] = useState<boolean>(false);
  const [lightboxData, setLightboxData] = useState<{ src: string; alt?: string } | null>(null);

  const totalSlides = SLIDES.length;

  const nextSlide = useCallback(() => {
    if (lightboxData) return;
    setCurrentIndex((prev) => Math.min(totalSlides - 1, prev + 1));
  }, [totalSlides, lightboxData]);

  const prevSlide = useCallback(() => {
    if (lightboxData) return;
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  }, [lightboxData]);

  const goToSlide = useCallback((index: number) => {
    if (lightboxData) return;
    setCurrentIndex(Math.max(0, Math.min(totalSlides - 1, index)));
  }, [totalSlides, lightboxData]);

  const toggleNotes = useCallback(() => {
    setShowNotes((prev) => !prev);
  }, []);

  const openLightbox = useCallback((src: string, alt?: string) => {
    setLightboxData({ src, alt });
  }, []);

  const closeLightbox = useCallback(() => {
    setLightboxData(null);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (lightboxData) return;
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault();
        nextSlide();
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        prevSlide();
      } else if (e.key === 'Home') {
        e.preventDefault();
        goToSlide(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        goToSlide(totalSlides - 1);
      } else if (e.key === 'n' || e.key === 'N') {
        toggleNotes();
      } else if (e.key === 'p' || e.key === 'P') {
        window.print();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nextSlide, prevSlide, goToSlide, toggleNotes, totalSlides, lightboxData]);

  // Touch gesture support
  useEffect(() => {
    let startX: number | null = null;

    const handleTouchStart = (e: TouchEvent) => {
      if (lightboxData) return;
      startX = e.touches[0].clientX;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (startX === null || lightboxData) return;
      const diffX = e.changedTouches[0].clientX - startX;
      if (Math.abs(diffX) > 50) {
        if (diffX < 0) nextSlide();
        else prevSlide();
      }
      startX = null;
    };

    window.addEventListener('touchstart', handleTouchStart, { passive: true });
    window.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [nextSlide, prevSlide, lightboxData]);

  const currentSlide = SLIDES[currentIndex];

  return (
    <div className="deck-container">
      <div className="slide-viewport">
        {SLIDES.map((slide, idx) => (
          <SlideViewer
            key={slide.id}
            slide={slide}
            isActive={idx === currentIndex}
            onOpenLightbox={openLightbox}
            onGoToSlide={goToSlide}
          />
        ))}
      </div>

      <SpeakerNotesPanel 
        isOpen={showNotes} 
        notes={currentSlide?.notes || ''} 
      />

      <NavigationChrome 
        currentIndex={currentIndex}
        totalSlides={totalSlides}
        onNext={nextSlide}
        onPrev={prevSlide}
      />

      <LightboxModal
        imgSrc={lightboxData?.src || null}
        imgAlt={lightboxData?.alt}
        onClose={closeLightbox}
      />
    </div>
  );
};

export default App;
