import { fallbackGallery } from "./mock-data";
import type {
  BenchmarkResult,
  Domain,
  DomainId,
  GalleryDocument,
  GenerateRequest,
  Health,
  InvoiceData,
  Job,
  JobStatus,
  Language,
  FinanceStatementData,
  HRRecordData,
  LegalContractData,
  MedicalNoteData,
  OCREvalReport,
  OCRSample,
  RetailProductData,
  Provider,
  RuleCheck,
  SupportConversationData,
} from "./types";

const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const API_URL = "/backend-api";
const REQUEST_TIMEOUT_MS = 8_000;

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = "";
      try {
        const errorBody = record(await response.json());
        detail = text(errorBody.detail ?? errorBody.message);
      } catch {
        // The status code still provides a useful fallback when the API returns no JSON body.
      }
      throw new ApiError(detail || `API request failed (${response.status})`, response.status);
    }

    if (response.status === 204) return {};
    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("API request timed out");
    }
    throw new ApiError(error instanceof Error ? error.message : "Unable to reach the API");
  } finally {
    clearTimeout(timeout);
  }
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function numeric(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return fallback;
}

function bool(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function arrayPayload(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  const source = record(value);
  for (const key of ["items", "results", "data", "domains", "documents", "gallery", "benchmarks", "samples"]) {
    if (Array.isArray(source[key])) return source[key] as unknown[];
  }
  return [];
}

function percentScore(value: unknown, fallback: number): number {
  const score = numeric(value, fallback);
  const percent = score > 0 && score <= 1 ? score * 100 : score;
  return Math.round(Math.max(0, Math.min(100, percent)) * 10) / 10;
}

function language(value: unknown): Language {
  return value === "hi-IN" || value === "gu-IN" ? value : "en-IN";
}

function provider(value: unknown): Provider {
  return value === "nemo" ? "nemo" : "offline";
}

function rule(value: unknown, index: number): RuleCheck {
  const source = record(value);
  return {
    id: text(source.id ?? source.key, `rule-${index + 1}`),
    label: text(source.label ?? source.name ?? source.rule, `Validation rule ${index + 1}`),
    passed: bool(source.passed ?? source.valid ?? source.success),
    detail: text(source.detail ?? source.message) || undefined,
  };
}

export function resolveApiAssetUrl(value: unknown, baseUrl?: string): string | undefined {
  const url = text(value);
  if (!url) return undefined;
  if (!baseUrl && url.startsWith("/artifacts/")) {
    return `/backend-artifacts/${url.slice("/artifacts/".length)}`;
  }

  try {
    const resolved = new URL(url, `${baseUrl ?? API_ORIGIN}/`);
    return resolved.protocol === "http:" || resolved.protocol === "https:" ? resolved.toString() : undefined;
  } catch {
    return undefined;
  }
}

export function normalizeDocument(value: unknown, index = 0): GalleryDocument {
  const source = record(value);
  const seller = record(source.seller ?? source.vendor);
  const urls = record(source.file_urls ?? source.files ?? source.downloads ?? source.artifacts);
  const quality = record(source.quality_report ?? source.validation);
  const invoice = record(source.invoice);
  const medicalNote = record(source.medical_note ?? source.medicalNote);
  const conversation = record(source.conversation);
  const contract = record(source.contract);
  const statement = record(source.statement);
  const hrRecord = record(source.hr_record ?? source.hrRecord);
  const product = record(source.product);
  const domain = text(source.domain, "invoices");
  const structured = new Set(["healthcare", "support", "legal", "finance", "hr", "retail"]);
  const isHealthcare = domain === "healthcare";
  const isSupport = domain === "support";
  const isLegal = domain === "legal";
  const isInvoice = !structured.has(domain);
  const score = percentScore(
    source.validation_score ?? source.score ?? source.accuracy ?? quality.score,
    94,
  );
  const rulesRaw = Array.isArray(source.rules)
    ? source.rules
    : Array.isArray(source.rule_checks)
      ? source.rule_checks
      : [];
  const fallback = fallbackGallery[index % fallbackGallery.length];
  const vendor = isInvoice
    ? text(source.vendor ?? source.supplier ?? seller.name, fallback.vendor)
    : undefined;
  const fallbackTitle = isHealthcare
    ? "Synthetic clinical note"
    : isSupport
      ? "Synthetic support conversation"
      : isLegal
        ? "Synthetic legal contract"
        : domain === "finance"
          ? "Synthetic finance statement"
          : domain === "hr"
            ? "Synthetic HR record"
            : domain === "retail"
              ? "Synthetic retail product"
              : `Invoice · ${vendor || "Generated vendor"}`;

  return {
    id: text(source.id ?? source.document_id ?? source.invoice_number, `document-${index + 1}`),
    title: text(source.title ?? source.name, fallbackTitle),
    domain,
    language: language(source.language ?? source.language_code),
    provider: provider(source.provider),
    createdAt: text(source.created_at ?? source.createdAt, new Date().toISOString()),
    validationScore: score,
    status: source.status === "review" || score < 95 ? "review" : "validated",
    amount: isInvoice ? text(source.amount ?? source.total ?? source.total_amount, fallback.amount) : undefined,
    vendor,
    invoiceNumber: isInvoice ? text(source.invoice_number ?? source.invoiceNumber, fallback.invoiceNumber) : undefined,
    dueDate: isInvoice ? text(source.due_date ?? source.dueDate, fallback.dueDate) : undefined,
    fileUrls: {
      pdf: resolveApiAssetUrl(urls.pdf ?? source.pdf_url),
      image: resolveApiAssetUrl(urls.image ?? urls.png ?? source.image_url),
      degradedImage: resolveApiAssetUrl(urls.degraded_image ?? urls.degradedImage),
      json: resolveApiAssetUrl(urls.json ?? source.json_url),
    },
    rules: rulesRaw.length ? rulesRaw.map(rule) : isInvoice ? fallback.rules : [],
    invoice: Object.keys(invoice).length ? (invoice as unknown as InvoiceData) : undefined,
    medicalNote: Object.keys(medicalNote).length ? (medicalNote as unknown as MedicalNoteData) : undefined,
    conversation: Object.keys(conversation).length ? (conversation as unknown as SupportConversationData) : undefined,
    contract: Object.keys(contract).length ? (contract as unknown as LegalContractData) : undefined,
    statement: Object.keys(statement).length ? (statement as unknown as FinanceStatementData) : undefined,
    hrRecord: Object.keys(hrRecord).length ? (hrRecord as unknown as HRRecordData) : undefined,
    product: Object.keys(product).length ? (product as unknown as RetailProductData) : undefined,
  };
}

export function normalizeJob(value: unknown): Job {
  const source = record(value);
  const rawStatus = text(source.status ?? source.state, "queued").toLowerCase();
  const statusMap: Record<string, JobStatus> = {
    pending: "queued",
    queued: "queued",
    processing: "running",
    running: "running",
    complete: "completed",
    completed: "completed",
    success: "completed",
    failed: "failed",
    error: "failed",
  };
  const output = record(source.output);
  const resultsSource = source.results ?? source.documents ?? output.documents ?? output.results;

  return {
    id: text(source.id ?? source.job_id, "unknown-job"),
    status: statusMap[rawStatus] ?? "queued",
    progress: Math.max(
      0,
      Math.min(100, numeric(source.progress ?? source.percent, rawStatus === "completed" || rawStatus === "success" ? 100 : 0)),
    ),
    message: text(source.message ?? source.detail ?? source.error) || undefined,
    createdAt: text(source.created_at ?? source.createdAt) || undefined,
    results: arrayPayload(resultsSource).map(normalizeDocument),
  };
}

export function normalizeDomains(value: unknown): Domain[] {
  return arrayPayload(value).map((entry, index) => {
    const source = record(entry);
    const id = text(source.id ?? source.slug, `domain-${index + 1}`).toLowerCase();
    return {
      id,
      name: text(
        source.name ?? source.label,
        id.replace(/(^|-)(\w)/g, (_, __, character: string) => ` ${character.toUpperCase()}`).trim(),
      ),
      description: text(source.description, "Synthetic document generation domain."),
      available: bool(source.available ?? source.enabled, id === "invoices"),
      generated: numeric(source.generated ?? source.document_count ?? source.count),
      accuracy: percentScore(source.accuracy ?? source.validation_score, 0),
    };
  });
}

export function normalizeBenchmark(value: unknown, index = 0): BenchmarkResult {
  const source = record(value);
  const rawDomain = text(source.domain, "invoices");
  const domain = (["healthcare", "support", "legal", "finance", "hr", "retail"].includes(rawDomain) ? rawDomain : "invoices") as DomainId;
  return {
    id: text(source.id ?? source.benchmark_id, `bench-${index + 1}`),
    name: text(source.name ?? source.label, "Cross-domain quality benchmark"),
    domain,
    metricScope: text(source.metric_scope ?? source.metricScope, "deterministic validation consistency"),
    score: percentScore(source.score ?? source.accuracy ?? source.f1, 0),
    latencyMs: numeric(source.latency_ms ?? source.latency ?? source.mean_latency_ms, 0),
    throughput: numeric(source.throughput ?? source.documents_per_second ?? source.docs_per_second, 0),
    createdAt: text(source.created_at ?? source.createdAt, new Date().toISOString()),
  };
}

export function normalizeOCRSample(value: unknown): OCRSample {
  const source = record(value);
  const fileUrlsSource = record(source.file_urls ?? source.fileUrls);
  const fileUrls: Record<string, string> = {};
  for (const [key, item] of Object.entries(fileUrlsSource)) {
    if (typeof item === "string" && item) fileUrls[key] = item;
  }
  return {
    jobId: text(source.job_id ?? source.jobId),
    documentIndex: Math.max(0, Math.round(numeric(source.document_index ?? source.documentIndex, 0))),
    documentId: text(source.document_id ?? source.documentId) || undefined,
    title: text(source.title, "Invoice sample"),
    language: text(source.language) as Language | undefined,
    validationScore: source.validation_score == null && source.validationScore == null ? undefined : percentScore(source.validation_score ?? source.validationScore, 0),
    fileUrls,
    invoiceNumber: text(source.invoice_number ?? source.invoiceNumber) || undefined,
    grandTotal: text(source.grand_total ?? source.grandTotal) || undefined,
  };
}

export function normalizeOCRReport(value: unknown): OCREvalReport {
  const source = record(value);
  const groupsSource = record(source.groups);
  const groups: OCREvalReport["groups"] = {};
  for (const [name, raw] of Object.entries(groupsSource)) {
    const group = record(raw);
    groups[name] = {
      total: Math.round(numeric(group.total, 0)),
      correct: Math.round(numeric(group.correct, 0)),
      accuracy: percentScore(group.accuracy, 0),
    };
  }
  const comparisons = arrayPayload(source.comparisons).map((item) => {
    const row = record(item);
    return {
      field: text(row.field),
      group: text(row.group, "identity"),
      expected: row.expected == null ? null : text(row.expected),
      predicted: row.predicted == null ? null : text(row.predicted),
      matched: Boolean(row.matched),
    };
  });
  return {
    model: text(source.model, "user-ocr-model"),
    metricScope: text(source.metric_scope ?? source.metricScope, "OCR structure accuracy"),
    totalFields: Math.round(numeric(source.total_fields ?? source.totalFields, comparisons.length)),
    correctFields: Math.round(numeric(source.correct_fields ?? source.correctFields, comparisons.filter((row) => row.matched).length)),
    accuracy: percentScore(source.accuracy, 0),
    groups,
    comparisons,
    missingFields: arrayPayload(source.missing_fields ?? source.missingFields).map((item) => text(item)).filter(Boolean),
    incorrectFields: arrayPayload(source.incorrect_fields ?? source.incorrectFields).map((item) => text(item)).filter(Boolean),
    groundTruth: record(source.ground_truth ?? source.groundTruth),
    prediction: record(source.prediction),
    context: source.context == null ? null : record(source.context),
  };
}

export const api = {
  baseUrl: API_ORIGIN,

  async health(): Promise<Health> {
    const value = record(await request("/api/v1/health"));
    const status = text(value.status, "ok").toLowerCase();
    return {
      online: !["error", "offline", "unhealthy"].includes(status),
      service: text(value.service ?? value.name, "NV-SynthForge API"),
      version: text(value.version) || undefined,
      provider: text(value.provider) || undefined,
    };
  },

  async domains(): Promise<Domain[]> {
    return normalizeDomains(await request("/api/v1/domains"));
  },

  async gallery(): Promise<GalleryDocument[]> {
    return arrayPayload(await request("/api/v1/gallery")).map(normalizeDocument);
  },

  async generate(body: GenerateRequest): Promise<Job> {
    return normalizeJob(await request("/api/v1/generate", { method: "POST", body: JSON.stringify(body) }));
  },

  async job(id: string): Promise<Job> {
    return normalizeJob(await request(`/api/v1/jobs/${encodeURIComponent(id)}`));
  },

  async benchmarks(): Promise<BenchmarkResult[]> {
    return arrayPayload(await request("/api/v1/benchmarks")).map(normalizeBenchmark);
  },

  async benchmark(payload: Record<string, unknown>): Promise<BenchmarkResult> {
    return normalizeBenchmark(
      await request("/api/v1/benchmarks", { method: "POST", body: JSON.stringify(payload) }),
    );
  },

  async ocrSamples(): Promise<OCRSample[]> {
    return arrayPayload(await request("/api/v1/ocr/samples")).map(normalizeOCRSample);
  },

  async ocrEvaluate(payload: Record<string, unknown>): Promise<OCREvalReport> {
    return normalizeOCRReport(
      await request("/api/v1/ocr/evaluate", { method: "POST", body: JSON.stringify(payload) }),
    );
  },

  websocketUrl(id: string): string {
    const base = API_ORIGIN.replace(/^http:/, "ws:").replace(/^https:/, "wss:");
    return `${base}/api/v1/jobs/${encodeURIComponent(id)}/ws`;
  },
};
