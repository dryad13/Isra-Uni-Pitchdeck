import React from 'react';

interface ChromeProps {
  currentIndex: number;
  totalSlides: number;
  onNext: () => void;
  onPrev: () => void;
}

export const NavigationChrome: React.FC<ChromeProps> = ({
  currentIndex,
  totalSlides,
  onNext,
  onPrev,
}) => {
  const progressPercent = ((currentIndex + 1) / totalSlides) * 100;

  return (
    <div className="chrome-bar">
      <div 
        className="progress-bar-fill" 
        style={{ width: `${progressPercent}%` }} 
      />
      <div className="brand-mini">
        <img src="assets/logo.png" alt="Isra University Logo" />
        <span>OMR Console · Isra University</span>
      </div>
      <div className="slide-counter">
        {currentIndex + 1} / {totalSlides}
      </div>
      <div className="help-hint">
        ← → Space · N notes · P print · F11 fullscreen
      </div>
    </div>
  );
};
