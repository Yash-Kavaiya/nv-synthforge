import { StudioClient } from "@/components/studio-client";
import type { DomainId } from "@/lib/types";

export const metadata = {
  title: "Generation Studio · NV-SynthForge",
};

const ALLOWED = new Set(["invoices", "healthcare", "support", "legal", "finance", "hr", "retail"]);

export default async function StudioPage({ searchParams }: { searchParams: Promise<{ domain?: string }> }) {
  const params = await searchParams;
  const domain: DomainId = ALLOWED.has(params.domain ?? "") ? (params.domain as DomainId) : "invoices";
  return <StudioClient initialDomain={domain} />;
}
