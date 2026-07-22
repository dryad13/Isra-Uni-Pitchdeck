import { SlideData } from '../types';

export const SLIDES: SlideData[] = [
  {
    id: 1,
    type: 'title',
    logoSrc: 'assets/logo.png',
    eyebrow: 'Isra University · Karachi Campus',
    title: 'OMR Console',
    lead: 'On-premises bubble-sheet exam processing — scan, verify, score, and export without leaving the exam desk.',
    metaText: 'Stakeholder briefing · Optical Mark Recognition (not OCR)',
    notes: 'Welcome stakeholders. State this is OMR — bubble-sheet reading — not OCR. Isra’s on-prem exam processing console.'
  },
  {
    id: 2,
    type: 'bullets',
    eyebrow: 'Why we built this',
    title: 'The problem with vendor OMR',
    lead: 'Exam processing must be fast, accurate, and under university control — without perpetual licensing or cloud exposure.',
    bullets: [
      { title: 'ABBYY / vendor lock-in', text: 'recurring cost and dependency for a core academic operation' },
      { title: 'Exam-day volume', text: '~100 sheets per batch must move quickly with a clear exception path' },
      { title: 'Data residency', text: 'answer sheets and scores should stay on a university Windows PC, offline' }
    ],
    notes: 'Frame the pain: vendor dependency, cost, and the need for offline control of exam data on campus.'
  },
  {
    id: 3,
    type: 'flow',
    eyebrow: 'The solution',
    title: 'One console. End to end.',
    lead: 'OMR Console replaces the vendor stack with an Isra-owned Windows application beside a Canon scanner.',
    notes: 'Walk the five-step pipeline once. This is the spine of the rest of the talk.'
  },
  {
    id: 4,
    type: 'outcomes',
    eyebrow: 'Outcomes',
    title: 'What success looks like',
    outcomes: [
      { title: 'Fully offline', description: 'Localhost only · no post-install internet · data stays on disk' },
      { title: '~100 sheets / batch', description: 'Target ≤1.5 seconds per page on the operator workstation' },
      { title: 'Secure Score', description: 'Blanks and multi-marks excluded from the denominator — fairer scoring' },
      { title: 'CSV & Excel export', description: 'Literal (A/B/C/D) or binary (1/0) · session or full program' },
      { title: 'University-owned stack', description: 'ABBYY replacement with Isra branding and on-prem control' },
      { title: 'Human-in-the-loop', description: 'Only exceptions need review — clean sheets flow automatically' }
    ],
    notes: 'Hit the leadership bullets: offline, speed, Secure Score, ownership. Pause for questions before product tour.'
  },
  {
    id: 5,
    type: 'two-col',
    eyebrow: 'Product tour',
    title: 'OMR Console at a glance',
    imgSrc: 'assets/screenshots/01-shell-run-exam.png',
    imgAlt: 'OMR Console Run exam screen',
    shotHeavy: true,
    navActiveItem: 'Run exam',
    captions: [
      { label: 'Operator home', text: 'Three-step workflow: exam → key → process' },
      { label: 'Isra branded', text: 'University logo on every screen — white canvas, trust-first UI' },
      { label: 'Desktop Windows', text: 'Runs as OMR.exe beside the scanner' }
    ],
    notes: 'Orient to the five nav items. This is the operator’s daily home.'
  },
  {
    id: 6,
    type: 'cards',
    eyebrow: 'People',
    title: 'Who uses it',
    cards: [
      { title: 'Exam operators', description: 'Daily desk workflow: set up sittings, process stacks, clear the review queue, export scores.' },
      { title: 'Academic admins', description: 'Define exam programs, answer keys, subject splits, and student rosters.' },
      { title: 'QA / IT', description: 'Layout calibrator, Accuracy Lab, Canon dropzone setup, database backups.' }
    ],
    notes: 'Map personas so IT, ops, and academics know their lane.'
  },
  {
    id: 7,
    type: 'two-col',
    eyebrow: 'Sheet model',
    title: 'Isra answer sheet families',
    imgSrc: 'assets/screenshots/13-isra-sheet-sample.png',
    imgAlt: 'Isra 150Q sample sheet',
    shotHeavy: true,
    captions: [
      { label: '150Q family', text: '5 columns × 30 questions — primary template' },
      { label: '60Q family', text: '4 × 15 layout for shorter sittings' },
      { label: 'Roll number', text: '6-digit bubble grid only (barcode ignored)' },
      { label: 'Multi-sitting', text: 'Global Q numbering across sessions (e.g. Q1–20 then Q21–50)' }
    ],
    notes: 'Show physical sheet. Emphasize bubble roll only — barcode ignored.'
  },
  {
    id: 8,
    type: 'two-col',
    eyebrow: 'Workflow · Step 1',
    title: 'Choose exam and session',
    imgSrc: 'assets/screenshots/02-step-exam-session.png',
    imgAlt: 'Exam and session selection',
    shotHeavy: true,
    captions: [
      { label: 'Exam programs', text: 'Recurring series with cumulative master keys' },
      { label: 'Sessions', text: 'Each sitting gets its own Q slice and path layout' },
      { label: 'Why it matters', text: 'No re-keying the entire paper for every weekly test' }
    ],
    notes: 'Demo narrative: create program, pick session, see global Q range.'
  },
  {
    id: 9,
    type: 'two-col',
    eyebrow: 'Workflow · Step 2',
    title: 'Load the answer key',
    imgSrc: 'assets/screenshots/03-step-answer-key.png',
    imgAlt: 'Answer key coverage and grid',
    shotHeavy: true,
    captions: [
      { label: 'Three ways in', text: 'CSV/Excel · manual grid · marked sheet' },
      { label: 'Coverage map', text: 'See which global ranges are complete' },
      { label: 'Guardrail', text: 'Processing blocked until the session slice is fully keyed' }
    ],
    notes: 'Coverage map is the trust signal — scanning blocked until key is complete.'
  },
  {
    id: 10,
    type: 'two-col',
    eyebrow: 'Workflow · Step 3',
    title: 'Process scanned sheets',
    imgSrc: 'assets/screenshots/04-step-scanning.png',
    imgAlt: 'Batch processing progress',
    shotHeavy: true,
    captions: [
      { label: 'Dropzone', text: 'Canon scans land in C:\\OMR_Dropzone\\ and are picked up automatically' },
      { label: 'Live progress', text: 'Processed count, review flags, average page time' },
      { label: 'Fallback', text: 'Manual file upload when needed' }
    ],
    notes: 'Canon dropzone story. Mention upload fallback.'
  },
  {
    id: 11,
    type: 'two-col',
    eyebrow: 'Workflow · Results',
    title: 'Review exceptions, not every sheet',
    imgSrc: 'assets/screenshots/05-results-queue.png',
    imgAlt: 'Results review queue',
    shotHeavy: true,
    captions: [
      { label: 'Flagged only', text: 'Blanks, multi-marks, ambiguous rolls' },
      { label: 'Queue badge', text: 'Pending count stays visible in navigation' },
      { label: 'Operator focus', text: 'Batch review clears exceptions so scoring can finish' }
    ],
    notes: 'Only exceptions need humans. Pending badge keeps the queue visible.'
  },
  {
    id: 12,
    type: 'two-col',
    eyebrow: 'Workflow · Verification',
    title: 'Confirm what the machine flagged',
    imgSrc: 'assets/screenshots/06-batch-review.png',
    imgAlt: 'Anomaly override review',
    shotHeavy: true,
    captions: [
      { label: 'Crop viewer', text: 'See the exact bubble region in question' },
      { label: 'Override', text: 'Set A/B/C/D or Blank · confirm, skip, or flag' },
      { label: 'Sheet ↔ Global Q', text: 'Operators see both numbers during multi-sitting exams' }
    ],
    notes: 'Show crop + override. Mention L hotkey briefly.'
  },
  {
    id: 13,
    type: 'two-col',
    eyebrow: 'Workflow · Audit',
    title: 'Per-sheet question audit',
    imgSrc: 'assets/screenshots/07-sheet-detail.png',
    imgAlt: 'Sheet detail audit table',
    shotHeavy: true,
    captions: [
      { label: 'Read vs key', text: 'Every question comparable at a glance' },
      { label: 'Overrides marked', text: 'Human decisions remain visible' },
      { label: 'Trust', text: 'Supports student queries and internal QA' }
    ],
    notes: 'Auditability for disputes and academic integrity.'
  },
  {
    id: 14,
    type: 'two-col',
    eyebrow: 'Workflow · Reports',
    title: 'Scores and operational export',
    imgSrc: 'assets/screenshots/08-reports-export.png',
    imgAlt: 'Reports and Secure Score export',
    shotHeavy: true,
    captions: [
      { label: 'Secure Score & %', text: 'Side-by-side for fair comparison' },
      { label: 'Export modes', text: 'Literal or binary · CSV or Excel' },
      { label: 'Scope', text: 'One session or cumulative program — this is core ops, not analytics' }
    ],
    notes: 'Clarify this is operational export — not the analytics add-on.'
  },
  {
    id: 15,
    type: 'two-col',
    eyebrow: 'Workflow · Roster',
    title: 'Student roster',
    imgSrc: 'assets/screenshots/09-roster.png',
    imgAlt: 'Student roster screen',
    shotHeavy: true,
    captions: [
      { label: 'CSV / Excel upload', text: 'Roll lists per exam program' },
      { label: 'Unknown rolls', text: 'Surfaced for review instead of silent mis-score' },
      { label: 'Sections', text: 'Supports later academic grouping' }
    ],
    notes: 'Unknown rolls go to review — protects result integrity.'
  },
  {
    id: 16,
    type: 'two-col',
    eyebrow: 'Tools',
    title: 'Calibrator & Accuracy Lab',
    twoImages: ['assets/screenshots/10-tools-hub.png', 'assets/screenshots/11-calibrator.png'],
    lead: 'For QA and IT: tune bubble layouts and validate read accuracy on fixtures before exam day.',
    notes: 'Keep brief — QA/IT only. Don’t digress into calibration detail unless asked.'
  },
  {
    id: 17,
    type: 'pipeline',
    eyebrow: 'How it works',
    title: 'From image to answers',
    pipeSteps: [
      { number: '01', title: 'Align', description: 'Corner bullseyes → perspective warp so every sheet lines up' },
      { number: '02', title: 'Roll', description: 'Decode the 6-digit bubble matrix' },
      { number: '03', title: 'Bubbles', description: 'Measure A/B/C/D fill density with dynamic threshold' },
      { number: '04', title: 'Flag', description: 'Blank and multi-mark anomalies go to human review' }
    ],
    notes: 'Light technical — four steps only. No code.'
  },
  {
    id: 18,
    type: 'bullets',
    eyebrow: 'Security',
    title: 'Data stays on campus',
    bullets: [
      { title: 'Localhost only', text: 'UI and API bind to 127.0.0.1:8080' },
      { title: 'SQLite on disk', text: 'exam data in a local database with backup scripts' },
      { title: 'No cloud telemetry', text: 'designed for fully offline operation after install' },
      { title: 'Audit trail', text: 'answer-key changes and overrides remain traceable' }
    ],
    notes: 'Leadership assurance slide. Localhost + SQLite + no telemetry.'
  },
  {
    id: 19,
    type: 'cards',
    eyebrow: 'Deploy',
    title: 'Hardware & deployment',
    cards: [
      { title: 'Workstation', description: 'Windows PC next to the scanner · OMR.exe one-folder package' },
      { title: 'Scanner', description: 'Canon imageFORMULA DR-M140 → folder profile into the dropzone' },
      { title: 'Backup', description: 'Nightly omr.db backup · documented acceptance checklist' }
    ],
    notes: 'Hardware reality: Windows PC + Canon. Demo pack for training.'
  },
  {
    id: 20,
    type: 'two-col',
    eyebrow: 'Quality',
    title: 'Built-in quality controls',
    imgSrc: 'assets/screenshots/12-accuracy-lab.png',
    imgAlt: 'Accuracy Lab results',
    shotHeavy: true,
    captions: [
      { label: 'Anomaly crops', text: 'Operators see the disputed region' },
      { label: 'Verification queue', text: 'Nothing silent — flags must be cleared' },
      { label: 'Accuracy Lab', text: 'Fixture runs and threshold tuning before go-live' }
    ],
    notes: 'Close the trust act with Accuracy Lab proof point.'
  },
  {
    id: 21,
    type: 'bullets',
    isAddon: true,
    addonBadgeText: 'ADD-ON',
    addonSubTag: 'OPTIONAL',
    title: 'Result Analytics Dashboard',
    lead: 'Core product gets you scored results. This add-on turns those results into academic insight — for faculty and the Academic Council, not the daily OMR operator.',
    bullets: [
      { text: 'Ships after core go-live — does not block exam processing' },
      { text: 'Uses data the OMR Console already produces' },
      { text: 'Does not replace operational Reports (Secure Score / CSV export)' }
    ],
    notes: 'PAUSE. Reframe: core is done. This block is optional add-on for faculty/council. Do not imply it blocks go-live.'
  },
  {
    id: 22,
    type: 'two-col',
    isAddon: true,
    addonBadgeText: 'ADD-ON',
    addonSubTag: 'ITEM ANALYSIS',
    title: 'Per-question item analysis',
    imgSrc: 'assets/screenshots/15-addon-item-analysis.png',
    imgAlt: 'Item analysis mockup',
    shotHeavy: true,
    captions: [
      { label: 'Difficulty view', text: '% correct, blank rate, multi-mark rate per question' },
      { label: 'Distractors', text: 'A/B/C/D distribution shows where students went' },
      { label: 'Paper quality', text: 'Flag weak or ambiguous items before the next sitting' },
      { label: 'Preview', text: 'Concept mockup — not required for go-live' }
    ],
    notes: 'Walk Q34 example — weak item for paper review.'
  },
  {
    id: 23,
    type: 'two-col',
    isAddon: true,
    addonBadgeText: 'ADD-ON',
    addonSubTag: 'TRENDS',
    title: 'Section & semester performance',
    imgSrc: 'assets/screenshots/16-addon-trends.png',
    imgAlt: 'Trends mockup',
    shotHeavy: true,
    captions: [
      { label: 'Cohort tracking', text: 'Compare sections across sittings' },
      { label: 'Program view', text: 'Spot rising or falling subjects over a semester' },
      { label: 'Actionable', text: 'Gives deans a signal beyond a single exam average' }
    ],
    notes: 'Section B declining — council-relevant signal.'
  },
  {
    id: 24,
    type: 'two-col',
    isAddon: true,
    addonBadgeText: 'ADD-ON',
    addonSubTag: 'EXPORTS',
    title: 'Faculty & council-ready reports',
    imgSrc: 'assets/screenshots/17-addon-export-report.png',
    imgAlt: 'Analytics export report mockup',
    shotHeavy: true,
    captions: [
      { label: 'Meeting packs', text: 'PDF / Excel briefs with findings and recommendations' },
      { label: 'Audience', text: 'Faculty review and Academic Council — not the scan desk' },
      { label: 'Optional pilot', text: 'Can follow core go-live when the university is ready' }
    ],
    notes: 'Council-ready pack. Invite interest; don’t sell hard.'
  },
  {
    id: 25,
    type: 'bullets',
    eyebrow: 'Optional live demo',
    title: 'Five-minute path (core product)',
    bullets: [
      { text: 'Open Run exam → select program & session' },
      { text: 'Show answer key coverage for the sitting' },
      { text: 'Drop 2–3 sample scans into the dropzone (or upload)' },
      { text: 'Open Results → clear one flagged item' },
      { text: 'Open Reports → show Secure Score and export' }
    ],
    notes: 'If doing live demo: Run exam → key → drop samples → Results → Reports. Core only.'
  },
  {
    id: 26,
    type: 'cards',
    eyebrow: 'Status',
    title: 'Roadmap',
    cards: [
      { title: 'Core console', description: 'Run exam · verify · score · export · roster · offline Windows deploy' },
      { title: 'QA polish', description: 'Calibrator and Accuracy Lab continue to harden sheet families' },
      { title: 'Add-on (phased)', description: 'Result Analytics Dashboard — item analysis, trends, council exports', accent: true }
    ],
    notes: 'Be honest: core path vs polish vs add-on phase.'
  },
  {
    id: 27,
    type: 'ask-list',
    eyebrow: 'Next steps',
    title: 'What we need from you',
    askList: [
      { boldText: 'core OMR Console go-live', text: 'Approve for the exam workstation' },
      { boldText: 'operator training', text: 'Schedule (one sitting is enough to start)' },
      { boldText: 'Canon DR-M140', text: 'Confirm dropzone profile on the target PC' },
      { boldText: 'Optional:', text: 'register interest / pilot for the Result Analytics add-on', optional: true }
    ],
    notes: 'Close with clear asks. Last item is optional analytics interest.'
  },
  {
    id: 28,
    type: 'bullets',
    appendixTag: 'APPENDIX · Q&A',
    title: 'Secure Score formula',
    lead: 'Secure Score = correct ÷ (total − blank − multi) × 100',
    bullets: [
      { text: 'Blanks and multi-marks do not count as wrong' },
      { text: 'Percentage still available side-by-side for legacy comparison' },
      { text: 'Negative marking is configurable per session when required' }
    ],
    notes: 'Q&A only.'
  },
  {
    id: 29,
    type: 'matrix',
    appendixTag: 'APPENDIX · Q&A',
    title: 'Core vs ABBYY (feature view)',
    matrixData: [
      { capability: 'On-prem / offline', omrConsole: 'Yes', vendorOmr: 'Varies / license', omrCheck: true },
      { capability: 'Isra sheet templates', omrConsole: '150Q / 60Q calibrated', vendorOmr: 'Custom setup cost', omrCheck: true },
      { capability: 'Verification workflow', omrConsole: 'Built-in', vendorOmr: 'Varies', omrCheck: true },
      { capability: 'Multi-sitting master key', omrConsole: 'Yes', vendorOmr: 'Often manual', omrCheck: true },
      { capability: 'University-owned stack', omrConsole: 'Yes', vendorOmr: 'Vendor lock-in', omrCheck: true, vendorCheck: false },
      { capability: 'Analytics add-on', omrConsole: 'Optional phased', vendorOmr: 'Separate products' }
    ],
    notes: 'Q&A only.'
  },
  {
    id: 30,
    type: 'bullets',
    appendixTag: 'APPENDIX · ANALYTICS GLOSSARY',
    title: 'Analytics metrics (add-on)',
    bullets: [
      { title: 'Item difficulty', text: '% of students answering correctly' },
      { title: 'Blank / multi rates', text: 'signal ambiguous stems or poor bubbling' },
      { title: 'Distractor distribution', text: 'which wrong options attracted responses' },
      { title: 'Section trend', text: 'mean Secure Score across sittings for a cohort' }
    ],
    notes: 'Q&A only for faculty.'
  }
];
