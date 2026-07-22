import React from 'react';

interface CardProps {
  title: string;
  description: string;
  accent?: boolean;
  children?: React.ReactNode;
}

export const AstryxCard: React.FC<CardProps> = ({ title, description, accent, children }) => {
  return (
    <div 
      className="astryx-card"
      style={accent ? { borderColor: '#C0B6F2', backgroundColor: '#EAE6FF' } : undefined}
    >
      <h3 style={accent ? { color: 'var(--addon)' } : undefined}>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
};

interface BadgeProps {
  text: string;
  subTag?: string;
  variant?: 'addon' | 'primary' | 'success';
}

export const AstryxBadge: React.FC<BadgeProps> = ({ text, subTag, variant = 'addon' }) => {
  return (
    <div className={`astryx-badge ${variant}`}>
      <span>{text}</span>
      {subTag && <span className="sub-tag">{subTag}</span>}
    </div>
  );
};

interface FlowSvgProps {
  className?: string;
}

export const AstryxFlowSvg: React.FC<FlowSvgProps> = () => {
  return (
    <svg viewBox="0 0 920 180" width="100%" style={{ maxWidth: '1100px', marginTop: '8px', flex: '0 0 auto' }} aria-hidden="true">
      <rect x="10" y="45" width="150" height="80" rx="8" fill="#F4F5F7" stroke="#DFE1E6" strokeWidth="2"/>
      <text x="85" y="92" textAnchor="middle" fontSize="18" fontWeight="600" fill="#172B4D" fontFamily="Segoe UI,sans-serif">Canon DR-M140</text>
      <path d="M165 85 H205" stroke="#6B778C" strokeWidth="3"/>
      <polygon points="205,78 220,85 205,92" fill="#6B778C"/>
      <rect x="225" y="45" width="160" height="80" rx="8" fill="#DEEBFF" stroke="#B3D4FF" strokeWidth="2"/>
      <text x="305" y="82" textAnchor="middle" fontSize="17" fontWeight="700" fill="#0747A6" fontFamily="Segoe UI,sans-serif">Dropzone</text>
      <text x="305" y="106" textAnchor="middle" fontSize="14" fill="#6B778C" fontFamily="Segoe UI,sans-serif">auto-ingest</text>
      <path d="M390 85 H430" stroke="#6B778C" strokeWidth="3"/>
      <polygon points="430,78 445,85 430,92" fill="#6B778C"/>
      <rect x="450" y="45" width="170" height="80" rx="8" fill="#0052CC"/>
      <text x="535" y="82" textAnchor="middle" fontSize="17" fontWeight="700" fill="#fff" fontFamily="Segoe UI,sans-serif">OMR Pipeline</text>
      <text x="535" y="106" textAnchor="middle" fontSize="14" fill="#DEEBFF" fontFamily="Segoe UI,sans-serif">align · roll · bubbles</text>
      <path d="M625 85 H665" stroke="#6B778C" strokeWidth="3"/>
      <polygon points="665,78 680,85 665,92" fill="#6B778C"/>
      <rect x="685" y="45" width="110" height="80" rx="8" fill="#F4F5F7" stroke="#DFE1E6" strokeWidth="2"/>
      <text x="740" y="92" textAnchor="middle" fontSize="17" fontWeight="600" fill="#172B4D" fontFamily="Segoe UI,sans-serif">Verify</text>
      <path d="M800 85 H830" stroke="#6B778C" strokeWidth="3"/>
      <polygon points="830,78 845,85 830,92" fill="#6B778C"/>
      <rect x="850" y="45" width="60" height="80" rx="8" fill="#E3FCEF" stroke="#ABF5D1" strokeWidth="2"/>
      <text x="880" y="92" textAnchor="middle" fontSize="15" fontWeight="700" fill="#006644" fontFamily="Segoe UI,sans-serif">CSV</text>
    </svg>
  );
};
