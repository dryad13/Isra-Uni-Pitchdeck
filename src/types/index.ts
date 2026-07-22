export type SlideType = 
  | 'title'
  | 'bullets'
  | 'flow'
  | 'outcomes'
  | 'two-col'
  | 'cards'
  | 'pipeline'
  | 'ask-list'
  | 'matrix'
  | 'formula';

export interface CardItem {
  title: string;
  description: string;
  accent?: boolean;
}

export interface OutcomeItem {
  title: string;
  description: string;
}

export interface PipeStepItem {
  number: string;
  title: string;
  description: string;
}

export interface CaptionItem {
  label: string;
  text: string;
}

export interface AskListItem {
  text: string;
  boldText?: string;
  optional?: boolean;
}

export interface MatrixRow {
  capability: string;
  omrConsole: string;
  vendorOmr: string;
  omrCheck?: boolean;
  vendorCheck?: boolean;
}

export interface SlideData {
  id: number;
  type: SlideType;
  eyebrow?: string;
  title: string;
  lead?: string;
  notes: string;
  isAddon?: boolean;
  addonBadgeText?: string;
  addonSubTag?: string;
  appendixTag?: string;
  
  // Slide specific fields
  logoSrc?: string;
  metaText?: string;
  bullets?: Array<{ title?: string; text: string }>;
  cards?: CardItem[];
  outcomes?: OutcomeItem[];
  pipeSteps?: PipeStepItem[];
  imgSrc?: string;
  imgAlt?: string;
  shotHeavy?: boolean;
  captions?: CaptionItem[];
  navActiveItem?: string;
  twoImages?: string[];
  askList?: AskListItem[];
  matrixData?: MatrixRow[];
  formula?: string;
}
