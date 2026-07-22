import React from 'react';

interface SpeakerNotesPanelProps {
  isOpen: boolean;
  notes: string;
}

export const SpeakerNotesPanel: React.FC<SpeakerNotesPanelProps> = ({ isOpen, notes }) => {
  if (!isOpen) return null;

  return (
    <div className="notes-panel">
      <h4>Speaker Notes</h4>
      <p>{notes || 'No speaker notes for this slide.'}</p>
    </div>
  );
};
