import React from 'react';
import { SlideData } from '../types';
import { AstryxCard, AstryxBadge, AstryxFlowSvg } from './astryx/AstryxComponents';

interface SlideViewerProps {
  slide: SlideData;
  isActive: boolean;
  onOpenLightbox?: (imgSrc: string, imgAlt?: string) => void;
  onGoToSlide?: (slideIndex: number) => void;
}

const TAB_SLIDE_INDEX_MAP: Record<string, number> = {
  'Run exam': 4,  // Slide 5 (index 4)
  'Results': 10,  // Slide 11 (index 10)
  'Reports': 13,  // Slide 14 (index 13)
  'Roster': 14,   // Slide 15 (index 14)
  'Tools': 15,    // Slide 16 (index 15)
};

export const SlideViewer: React.FC<SlideViewerProps> = ({
  slide,
  isActive,
  onOpenLightbox,
  onGoToSlide,
}) => {
  const containerClasses = [
    'astryx-slide',
    isActive ? 'active' : '',
    slide.isAddon ? 'addon' : '',
    slide.type === 'title' ? 'title-slide' : ''
  ].filter(Boolean).join(' ');

  const handleImageClick = (src: string, alt?: string) => {
    if (onOpenLightbox) {
      onOpenLightbox(src, alt);
    }
  };

  const handleTabClick = (tabName: string) => {
    const targetIndex = TAB_SLIDE_INDEX_MAP[tabName];
    if (targetIndex !== undefined && onGoToSlide) {
      onGoToSlide(targetIndex);
    }
  };

  return (
    <div className={containerClasses}>
      <div className="slide-content-wrapper">
        {/* Appendix Tag */}
        {slide.appendixTag && (
          <div className="appendix-tag">{slide.appendixTag}</div>
        )}

        {/* Addon Badge */}
        {slide.isAddon && (
          <AstryxBadge 
            text={slide.addonBadgeText || 'ADD-ON'} 
            subTag={slide.addonSubTag} 
          />
        )}

        {/* Eyebrow label */}
        {slide.eyebrow && !slide.isAddon && (
          <div className="eyebrow-label">{slide.eyebrow}</div>
        )}

        {/* Title slide specific logo */}
        {slide.type === 'title' && slide.logoSrc && (
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <img 
              src={slide.logoSrc} 
              alt="Isra University Logo" 
              style={{ height: 'clamp(110px, 16vh, 160px)', width: 'auto' }} 
            />
          </div>
        )}

        {/* Title */}
        <h1 className="slide-title" style={slide.type === 'title' ? { textAlign: 'center', margin: '0 auto 20px' } : undefined}>
          {slide.title}
        </h1>

        {/* Lead paragraph */}
        {slide.lead && (
          <p 
            className="lead-text" 
            style={
              slide.type === 'title' 
                ? { textAlign: 'center', marginLeft: 'auto', marginRight: 'auto' } 
                : slide.twoImages 
                  ? { marginBottom: '16px', fontSize: 'clamp(20px, 1.8vw, 24px)' } 
                  : undefined
            }
          >
            {slide.lead}
          </p>
        )}

        {/* Title slide Meta */}
        {slide.type === 'title' && slide.metaText && (
          <div style={{ textAlign: 'center', marginTop: '28px', color: 'var(--muted)', fontSize: '18px' }}>
            {slide.metaText}
          </div>
        )}

        {/* Bullets Slide */}
        {slide.type === 'bullets' && slide.bullets && (
          <ul className="bullets-list">
            {slide.bullets.map((b, idx) => (
              <li key={idx}>
                {b.title ? (
                  <>
                    <strong style={{ color: 'var(--ink)' }}>{b.title}</strong> — {b.text}
                  </>
                ) : (
                  <span>{b.text}</span>
                )}
              </li>
            ))}
          </ul>
        )}

        {/* Flow Slide */}
        {slide.type === 'flow' && (
          <>
            <div className="flow-diagram">
              <div className="flow-node">Scan</div><div className="flow-arrow">→</div>
              <div className="flow-node">Auto-read</div><div className="flow-arrow">→</div>
              <div className="flow-node">Verify</div><div className="flow-arrow">→</div>
              <div className="flow-node">Score</div><div className="flow-arrow">→</div>
              <div className="flow-node">Export</div>
            </div>
            <AstryxFlowSvg />
          </>
        )}

        {/* Outcomes Grid */}
        {slide.type === 'outcomes' && slide.outcomes && (
          <div className="outcomes-grid">
            {slide.outcomes.map((item, idx) => (
              <div key={idx} className="outcome-box">
                <b>{item.title}</b>
                <span>{item.description}</span>
              </div>
            ))}
          </div>
        )}

        {/* Full-width Two Images Slide (e.g. Slide 16 Tools) */}
        {slide.twoImages && (
          <>
            {slide.navActiveItem && (
              <div className="nav-map" style={{ marginBottom: '16px' }}>
                {['Run exam', 'Results', 'Reports', 'Roster', 'Tools'].map((item) => (
                  <button
                    key={item}
                    type="button"
                    className={item === slide.navActiveItem ? 'on' : ''}
                    onClick={() => handleTabClick(item)}
                    title={`Jump to ${item}`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            )}
            <div className="two-images-grid">
              <div 
                className="shot-wrap zoomable" 
                onClick={() => handleImageClick(slide.twoImages![0], 'Tools Hub')}
                title="Click to expand full screen"
              >
                <img src={slide.twoImages[0]} alt="Tools Hub" />
                <div className="zoom-hint">🔍 Click to expand</div>
              </div>
              <div 
                className="shot-wrap zoomable" 
                onClick={() => handleImageClick(slide.twoImages![1], 'Layout Calibrator')}
                title="Click to expand full screen"
              >
                <img src={slide.twoImages[1]} alt="Layout Calibrator" />
                <div className="zoom-hint">🔍 Click to expand</div>
              </div>
            </div>
          </>
        )}

        {/* Single Image Two Column Screenshot Slide */}
        {slide.type === 'two-col' && !slide.twoImages && (
          <div className={`two-col-grid ${slide.shotHeavy ? 'shot-heavy' : ''}`}>
            {slide.imgSrc && (
              <div 
                className="shot-wrap zoomable"
                onClick={() => handleImageClick(slide.imgSrc!, slide.imgAlt)}
                title="Click to expand full screen"
              >
                <img src={slide.imgSrc} alt={slide.imgAlt || ''} />
                <div className="zoom-hint">🔍 Click to expand</div>
              </div>
            )}

            <div>
              {slide.navActiveItem && (
                <div className="nav-map">
                  {['Run exam', 'Results', 'Reports', 'Roster', 'Tools'].map((item) => (
                    <button
                      key={item}
                      type="button"
                      className={item === slide.navActiveItem ? 'on' : ''}
                      onClick={() => handleTabClick(item)}
                      title={`Jump to ${item}`}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              )}

              {slide.captions && (
                <ul className="caption-list">
                  {slide.captions.map((cap, idx) => (
                    <li key={idx}>
                      <strong>{cap.label}</strong>
                      <span>{cap.text}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* Cards Grid */}
        {slide.type === 'cards' && slide.cards && (
          <div className="cards-grid">
            {slide.cards.map((card, idx) => (
              <AstryxCard 
                key={idx} 
                title={card.title} 
                description={card.description} 
                accent={card.accent} 
              />
            ))}
          </div>
        )}

        {/* Pipeline Grid */}
        {slide.type === 'pipeline' && slide.pipeSteps && (
          <div className="pipeline-grid">
            {slide.pipeSteps.map((step, idx) => (
              <div key={idx} className="pipe-step">
                <div className="step-number">{step.number}</div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
            ))}
          </div>
        )}

        {/* Ask List */}
        {slide.type === 'ask-list' && slide.askList && (
          <ul className="ask-list">
            {slide.askList.map((item, idx) => (
              <li key={idx} className={item.optional ? 'optional-item' : ''}>
                <span className="checkbox-square" />
                <span>
                  {item.boldText && <strong>{item.boldText} </strong>}
                  {item.text}
                </span>
              </li>
            ))}
          </ul>
        )}

        {/* Matrix Table */}
        {slide.type === 'matrix' && slide.matrixData && (
          <table className="matrix-table">
            <thead>
              <tr>
                <th>Capability</th>
                <th>OMR Console</th>
                <th>Typical Vendor OMR</th>
              </tr>
            </thead>
            <tbody>
              {slide.matrixData.map((row, idx) => (
                <tr key={idx}>
                  <td>{row.capability}</td>
                  <td className={row.omrCheck ? 'check' : undefined}>
                    {row.omrConsole}
                  </td>
                  <td className={row.vendorCheck === false ? 'cross' : undefined}>
                    {row.vendorOmr}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
