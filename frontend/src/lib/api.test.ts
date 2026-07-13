import { describe, expect, it } from "vitest";
import {
  normalizeBenchmark,
  normalizeDocument,
  normalizeDomains,
  normalizeJob,
  resolveApiAssetUrl,
} from "./api";

describe("API response normalizers", () => {
  it("normalizes nested gallery documents and converts fractional quality scores", () => {
    const document = normalizeDocument({
      document_id: "inv-7",
      supplier: "Orbit Tools",
      language_code: "hi-IN",
      validation_score: 0.97,
      file_urls: { pdf: "/artifacts/inv-7.pdf", degraded_image: "/artifacts/inv-7-degraded.jpg" },
      invoice: {
        invoice_number: "INV-7",
        invoice_date: "2026-07-13",
        seller: { name: "Orbit Tools", gstin: "24ABCDE1234F1Z5", address: { line1: "1 Market Road", city: "Ahmedabad", state: "Gujarat", postal_code: "380001" } },
        buyer: { name: "Buyer Labs", gstin: "27ABCDE1234F1Z5", address: { line1: "2 Tech Park", city: "Mumbai", state: "Maharashtra", postal_code: "400001" } },
        items: [], currency: "INR", place_of_supply: "Maharashtra", subtotal: "100", cgst: "0", sgst: "0", igst: "18", grand_total: "118"
      },
      rule_checks: [{ key: "total", name: "Totals reconcile", valid: true }],
    });

    expect(document).toMatchObject({
      id: "inv-7",
      vendor: "Orbit Tools",
      language: "hi-IN",
      validationScore: 97,
      status: "validated",
    });
    expect(document.rules[0]).toMatchObject({ id: "total", passed: true });
    expect(document.invoice?.buyer.name).toBe("Buyer Labs");
    expect(document.fileUrls.degradedImage).toBe("/backend-artifacts/inv-7-degraded.jpg");
  });

  it("normalizes healthcare records without injecting invoice fallback fields", () => {
    const document = normalizeDocument({
      id: "med-1",
      title: "Medical note · MED-000042-0001",
      domain: "healthcare",
      language: "gu-IN",
      validation_score: 100,
      medical_note: {
        note_id: "MED-000042-0001",
        encounter_date: "2026-03-14",
        language: "gu-IN",
        patient: { patient_id: "SYN-PAT-041874", name: "Patient-1554", age: 38, gender: "female" },
        chief_complaint: "Fever and dry cough for three days",
        vitals: { temperature_c: 37.4, pulse_bpm: 78, systolic_mm_hg: 122, diastolic_mm_hg: 78, spo2_percent: 98 },
        soap: { subjective: "Symptoms reported", objective: "Exam findings", assessment: "Viral illness", plan: "Rest and review" },
        diagnoses: [{ icd10_code: "J06.9", description: "Acute upper respiratory infection" }],
        medications: [],
        synthetic: true,
        disclaimer: "Synthetic clinical record. Not for patient care.",
      },
      rules: [{ id: "soap_completeness", label: "SOAP complete", passed: true }],
      file_urls: { json: "/artifacts/medical-notes.json" },
    });

    expect(document.domain).toBe("healthcare");
    expect(document.medicalNote?.patient.name).toBe("Patient-1554");
    expect(document.medicalNote?.diagnoses[0].icd10_code).toBe("J06.9");
    expect(document.vendor).toBeUndefined();
    expect(document.fileUrls.json).toBe("/backend-artifacts/medical-notes.json");
  });

  it("normalizes terminal jobs and their output documents", () => {
    const job = normalizeJob({
      job_id: "job-12",
      state: "success",
      percent: "100",
      output: { documents: [{ id: "doc-1", score: 91 }] },
    });

    expect(job.status).toBe("completed");
    expect(job.progress).toBe(100);
    expect(job.results).toHaveLength(1);
    expect(job.results[0].id).toBe("doc-1");
  });

  it("accepts wrapped domain collections and humanizes missing names", () => {
    expect(normalizeDomains({ domains: [{ slug: "purchase-orders", enabled: true }] })).toEqual([
      expect.objectContaining({ id: "purchase-orders", name: "Purchase Orders", available: true }),
    ]);
  });

  it("normalizes benchmark metrics from fractional or alternate response fields", () => {
    expect(normalizeBenchmark({
      benchmark_id: "bench-4",
      accuracy: 0.984,
      latency: "142.5",
      documents_per_second: 7.2,
    })).toMatchObject({
      id: "bench-4",
      score: 98.4,
      latencyMs: 142.5,
      throughput: 7.2,
    });
  });

  it("normalizes customer-support conversations without invoice fallback fields", () => {
    const document = normalizeDocument({
      id: "support-1",
      title: "Support conversation · SUP-000314-0001",
      domain: "support",
      language: "hi-IN",
      validation_score: 100,
      conversation: {
        conversation_id: "SUP-000314-0001",
        customer_id: "SYN-CUST-130459",
        started_at: "2026-02-01T10:00:00Z",
        language: "hi-IN",
        industry: "telecom",
        channel: "chat",
        issue_type: "unexpected mobile-data charge",
        sentiment_arc: "recovery",
        resolution_status: "resolved",
        turns: [
          { turn_id: 1, role: "customer", text: "I need help.", sentiment: -0.8 },
          { turn_id: 2, role: "agent", text: "I resolved the issue.", sentiment: 0.9 },
        ],
        synthetic: true,
        disclaimer: "Synthetic customer-support conversation. Not a real customer interaction.",
      },
      rules: [{ id: "sentiment_arc", label: "Sentiment arc", passed: true }],
      file_urls: { json: "/artifacts/support-conversations.json" },
    });

    expect(document.domain).toBe("support");
    expect(document.conversation?.industry).toBe("telecom");
    expect(document.conversation?.turns[1].role).toBe("agent");
    expect(document.vendor).toBeUndefined();
    expect(document.amount).toBeUndefined();
    expect(document.fileUrls.json).toBe("/backend-artifacts/support-conversations.json");
  });

  it("preserves benchmark domain and metric scope", () => {
    expect(normalizeBenchmark({
      benchmark_id: "bench-support",
      domain: "support",
      metric_scope: "turn structure and sentiment-arc consistency",
      score: 100,
    })).toMatchObject({
      id: "bench-support",
      domain: "support",
      metricScope: "turn structure and sentiment-arc consistency",
    });
  });
});

describe("resolveApiAssetUrl", () => {
  it("keeps absolute URLs and anchors relative artifact URLs to the API", () => {
    expect(resolveApiAssetUrl("https://cdn.example.test/doc.pdf")).toBe("https://cdn.example.test/doc.pdf");
    expect(resolveApiAssetUrl("/artifacts/doc.pdf", "http://localhost:8000")).toBe("http://localhost:8000/artifacts/doc.pdf");
  });

  it("rejects unsafe URL schemes", () => {
    expect(resolveApiAssetUrl("javascript:alert(1)")).toBeUndefined();
  });
});
