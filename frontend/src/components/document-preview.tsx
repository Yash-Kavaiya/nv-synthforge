import { Activity, Bot, Headphones, HeartPulse, MessageSquareText, ShieldCheck, Stethoscope, UserRound } from "lucide-react";
import type { GalleryDocument } from "@/lib/types";
import { InvoicePreview } from "./invoice-preview";

export function DocumentPreview({ document, compact = false }: { document: GalleryDocument; compact?: boolean }) {
  if (document.domain === "healthcare" && document.medicalNote) {
    return <HealthcarePreview document={document} compact={compact} />;
  }
  if (document.domain === "support" && document.conversation) {
    return <SupportConversationPreview document={document} compact={compact} />;
  }
  return <InvoicePreview document={document} compact={compact} />;
}

export function HealthcarePreview({ document, compact }: { document: GalleryDocument; compact: boolean }) {
  const note = document.medicalNote!;
  const sections = [
    ["S", "Subjective", note.soap.subjective],
    ["O", "Objective", note.soap.objective],
    ["A", "Assessment", note.soap.assessment],
    ["P", "Plan", note.soap.plan],
  ];

  return (
    <div className="manifest clinical-note">
      <div className="clinical-accent" />
      <header className="clinical-head">
        <div><span className="clinical-mark"><HeartPulse aria-hidden="true" /> NV / CLINICAL</span><h2>Synthetic SOAP Note</h2><p>{note.note_id} · {formatDate(note.encounter_date)}</p></div>
        <span className="synthetic-chip"><ShieldCheck aria-hidden="true" /> SYNTHETIC</span>
      </header>

      <section className="clinical-patient">
        <div><small>PSEUDONYMOUS PATIENT</small><strong>{note.patient.name}</strong><span>{note.patient.patient_id}</span></div>
        <dl><div><dt>Age</dt><dd>{note.patient.age}</dd></div><div><dt>Gender</dt><dd>{note.patient.gender}</dd></div><div><dt>Locale</dt><dd>{note.language}</dd></div></dl>
      </section>

      <section className="clinical-complaint"><Stethoscope aria-hidden="true" /><div><small>CHIEF COMPLAINT</small><strong>{note.chief_complaint}</strong></div></section>

      <section className="vitals-strip" aria-label="Vital signs">
        <Vital label="TEMP" value={`${note.vitals.temperature_c}°C`} />
        <Vital label="PULSE" value={`${note.vitals.pulse_bpm}`} unit="bpm" />
        <Vital label="BP" value={`${note.vitals.systolic_mm_hg}/${note.vitals.diastolic_mm_hg}`} unit="mmHg" />
        <Vital label="SpO₂" value={`${note.vitals.spo2_percent}%`} />
      </section>

      <div className="soap-grid">
        {sections.slice(0, compact ? 2 : 4).map(([letter, title, body]) => <section key={letter}><span>{letter}</span><div><strong>{title}</strong><p>{body}</p></div></section>)}
      </div>

      <section className="clinical-codes">
        <div><small>DIAGNOSIS</small>{note.diagnoses.map((diagnosis) => <p key={diagnosis.icd10_code}><b>{diagnosis.icd10_code}</b> {diagnosis.description}</p>)}</div>
        {!compact ? <div><small>MEDICATION</small>{note.medications.length ? note.medications.map((medication) => <p key={`${medication.generic_name}-${medication.dose}`}><b>{medication.generic_name}</b> {medication.dose} · {medication.frequency}</p>) : <p>No medication prescribed</p>}</div> : null}
      </section>

      <footer className="clinical-footer"><Activity aria-hidden="true" /> {note.disclaimer}</footer>
    </div>
  );
}

function SupportConversationPreview({ document, compact }: { document: GalleryDocument; compact: boolean }) {
  const conversation = document.conversation!;
  const turns = compact ? conversation.turns.slice(0, 4) : conversation.turns;

  return (
    <div className={compact ? "manifest support-conversation support-compact" : "manifest support-conversation"}>
      <div className="support-accent" />
      <header className="support-head">
        <div className="support-brand"><span><Headphones aria-hidden="true" /></span><div><small>NV / SUPPORT</small><h2>Service Conversation</h2></div></div>
        <span className="synthetic-chip"><ShieldCheck aria-hidden="true" /> SYNTHETIC</span>
      </header>
      <section className="support-meta" style={{ marginTop: "24px" }}>
        <div><small>CONVERSATION</small><strong>{conversation.conversation_id}</strong></div>
        <div><small>INDUSTRY</small><strong>{conversation.industry}</strong></div>
        <div><small>CHANNEL</small><strong>{conversation.channel}</strong></div>
        <div><small>STATUS</small><strong className={conversation.resolution_status === "resolved" ? "support-resolved" : "support-escalated"}>{conversation.resolution_status}</strong></div>
      </section>
      <section className="support-issue" style={{ marginTop: "16px" }}><MessageSquareText aria-hidden="true" /><div><small>ISSUE TYPE</small><strong>{conversation.issue_type}</strong><span>{conversation.customer_id} · {conversation.language} · {conversation.sentiment_arc}</span></div></section>
      <div className="conversation-turns" style={{ marginTop: "20px" }}>
        {turns.map((turn) => (
          <article key={turn.turn_id} className={`conversation-turn turn-${turn.role}`}>
            <span className="turn-avatar">{turn.role === "customer" ? <UserRound aria-hidden="true" /> : <Bot aria-hidden="true" />}</span>
            <div><small>{turn.role} · turn {turn.turn_id} · {formatTime(turn.timestamp)}</small><p>{turn.text}</p></div>
            <i aria-label={`Sentiment ${turn.sentiment}`}>{turn.sentiment > 0.25 ? "+" : turn.sentiment < -0.25 ? "−" : "·"}</i>
          </article>
        ))}
      </div>
      {compact && conversation.turns.length > turns.length ? <p className="support-more">+ {conversation.turns.length - turns.length} validated turns</p> : null}
      <footer className="support-footer"><ShieldCheck aria-hidden="true" /> {conversation.disclaimer}</footer>
    </div>
  );
}

function Vital({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return <div><small>{label}</small><strong>{value}</strong>{unit ? <span>{unit}</span> : null}</div>;
}

function formatTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "time n/a" : parsed.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

function formatDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
