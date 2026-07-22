import React, { useEffect } from 'react';

interface LightboxModalProps {
  imgSrc: string | null;
  imgAlt?: string;
  onClose: () => void;
}

export const LightboxModal: React.FC<LightboxModalProps> = ({ imgSrc, imgAlt, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!imgSrc) return null;

  return (
    <div 
      className="lightbox-overlay" 
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(9, 30, 66, 0.85)',
        backdropFilter: 'blur(6px)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        animation: 'fadeIn 0.2s ease-out'
      }}
    >
      <div 
        className="lightbox-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'relative',
          maxWidth: '95vw',
          maxHeight: '92vh',
          background: '#fff',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center'
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'rgba(23, 43, 77, 0.8)',
            color: '#fff',
            border: 'none',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            fontSize: '20px',
            fontWeight: 'bold',
            cursor: 'pointer',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Close (Esc)"
        >
          ✕
        </button>
        <img 
          src={imgSrc} 
          alt={imgAlt || 'Enlarged screenshot'} 
          style={{
            maxWidth: '100%',
            maxHeight: '88vh',
            objectFit: 'contain',
            display: 'block'
          }}
        />
        {imgAlt && (
          <div style={{ padding: '12px 20px', background: '#F4F5F7', width: '100%', textAlign: 'center', color: '#172B4D', fontWeight: 600 }}>
            {imgAlt}
          </div>
        )}
      </div>
    </div>
  );
};
