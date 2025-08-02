export interface PatientType {
  first_name?: string;
  last_name?: string;
  demographic_no?: string;
  date_of_birth?: string;
  sex?: string;
  phone?: string;
  email?: string;
  location?: string[] | null;
  history: any[];
}

export interface Conversation {
  id: number | string;
  name: string;
  lastMessage: string;
  avatar: string;
  messages: { sender: string; text: string; usedTools?: string[] }[];
  participantId?: string;
  isAI?: boolean;
}

export interface EncounterType {
  note_id?: string;
  date_created?: string;
  provider_id?: string;
  note_text?: string | SOAPNotesType;
  note_type?: 'soap' | 'text';
  diagnostic_codes?: string[];
  status?: string;
  patient?: PatientType;
  score?: number;
  highlighted_note?: string;
}

export interface SOAPNotesType {
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
}

export interface EntityType {
  text: string;
  label: string;
  start_char: number;
  end_char: number;
  cui?: string;
  icd10cm?: string;
  icd10cm_name?: string;
}

export interface ICDAutoCoderResult {
  entities: EntityType[];
  normalized_entities: EntityType[];
  icd_codes: EntityType[];
  cached?: boolean;
}

export interface LabResult {
  result: number;
  reference_range: [number, number];
  units: string | null;
  description: string;
  notes?: string;
}

export interface LabResults {
  [key: string]: LabResult;
}

export interface LabResultsData {
  hematology: LabResults;
  differential_hematology: LabResults;
  general_chemistry: LabResults;
  serum_proteins: LabResults;
}

export interface PluginRoute {
  index?: boolean;
  path?: string;
  element: any;
}

export interface PluginWidget {
  name: string;
  path: string;
}
