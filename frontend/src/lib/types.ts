export type Provider = "offline" | "nemo";
export type Language = "en-IN" | "hi-IN" | "gu-IN";
export type DomainId = "invoices" | "healthcare" | "support" | "legal";
export type ClinicalProfile = "mixed" | "respiratory" | "cardiovascular" | "general";
export type SupportIndustry = "mixed" | "telecom" | "ecommerce" | "banking" | "saas";
export type SentimentArc = "recovery" | "steady-positive" | "escalation";
export type LegalDocumentType = "mixed" | "nda" | "service-agreement" | "msa";

export interface DegradationConfig {
  noise: number;
  blur: number;
  perspective: number;
  stamps: number;
}

export interface GenerateRequest {
  domain: DomainId;
  count: number;
  seed: number;
  provider: Provider;
  language: Language;
  render: boolean;
  degrade: boolean;
  degradation: DegradationConfig;
  healthcare: { clinical_profile: ClinicalProfile; include_medications: boolean };
  support: { industry: SupportIndustry; sentiment_arc: SentimentArc; max_turns: number };
  legal: { document_type: LegalDocumentType; max_clauses: number };
}

export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface RuleCheck {
  id: string;
  label: string;
  passed: boolean;
  detail?: string;
}

export interface InvoiceData {
  invoice_number: string;
  invoice_date: string;
  seller: { name: string; gstin: string; address: { line1: string; city: string; state: string; postal_code: string } };
  buyer: { name: string; gstin: string; address: { line1: string; city: string; state: string; postal_code: string } };
  items: Array<{ description: string; quantity: string; unit_price: string; line_total: string; gst_rate: string; hsn_sac: string }>;
  currency: string;
  place_of_supply: string;
  subtotal: string;
  cgst: string;
  sgst: string;
  igst: string;
  grand_total: string;
}

export interface MedicalNoteData {
  note_id: string;
  encounter_date: string;
  language: Language;
  patient: { patient_id: string; name: string; age: number; gender: string };
  chief_complaint: string;
  vitals: { temperature_c: number; pulse_bpm: number; systolic_mm_hg: number; diastolic_mm_hg: number; spo2_percent: number };
  soap: { subjective: string; objective: string; assessment: string; plan: string };
  diagnoses: Array<{ icd10_code: string; description: string }>;
  medications: Array<{ generic_name: string; dose: string; route: string; frequency: string; duration_days?: number }>;
  synthetic: true;
  disclaimer: string;
}

export interface SupportConversationData {
  conversation_id: string;
  customer_id: string;
  started_at: string;
  language: Language;
  industry: Exclude<SupportIndustry, "mixed">;
  channel: "chat" | "email" | "voice-transcript";
  issue_type: string;
  sentiment_arc: SentimentArc;
  resolution_status: "resolved" | "escalated";
  turns: Array<{ turn_id: number; role: "customer" | "agent"; timestamp: string; text: string; sentiment: number }>;
  synthetic: true;
  disclaimer: string;
}

export interface LegalContractData {
  contract_id: string;
  document_type: Exclude<LegalDocumentType, "mixed">;
  title: string;
  language: Language;
  effective_date: string;
  term_months: number;
  governing_law: string;
  parties: Array<{ party_id: string; name: string; role: string; jurisdiction: string }>;
  clauses: Array<{ clause_id: number; title: string; body: string; risk_flag: "none" | "medium" | "high" }>;
  confidentiality: boolean;
  synthetic: true;
  disclaimer: string;
}

export interface GalleryDocument {
  id: string;
  title: string;
  domain: string;
  language: Language;
  provider: Provider;
  createdAt: string;
  validationScore: number;
  status: "validated" | "review";
  amount?: string;
  vendor?: string;
  invoiceNumber?: string;
  dueDate?: string;
  fileUrls: {
    pdf?: string;
    image?: string;
    degradedImage?: string;
    json?: string;
  };
  rules: RuleCheck[];
  invoice?: InvoiceData;
  medicalNote?: MedicalNoteData;
  conversation?: SupportConversationData;
  contract?: LegalContractData;
}

export interface Job {
  id: string;
  status: JobStatus;
  progress: number;
  message?: string;
  createdAt?: string;
  results: GalleryDocument[];
}

export interface Domain {
  id: string;
  name: string;
  description: string;
  available: boolean;
  generated: number;
  accuracy: number;
}

export interface Health {
  online: boolean;
  service: string;
  version?: string;
  provider?: string;
}

export interface BenchmarkResult {
  id: string;
  name: string;
  domain: DomainId;
  metricScope: string;
  score: number;
  latencyMs: number;
  throughput: number;
  createdAt: string;
}
