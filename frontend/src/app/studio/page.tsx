import { StudioClient } from "@/components/studio-client";
import type { DomainId } from "@/lib/types";

export const metadata = {
  title: "Generation Studio",
};

export default async function StudioPage({ searchParams }: { searchParams: Promise<{ domain?: string }> }) {
  const params = await searchParams;
  const allowed = new Set(["invoices", "healthcare", "support", "legal"]);
  const domain: DomainId = allowed.has(params.domain ?? "") ? (params.domain as DomainId) : "invoices";
  return <StudioClient initialDomain={domain} />;
}
