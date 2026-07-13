import { StudioClient } from "@/components/studio-client";
import type { DomainId } from "@/lib/types";

export const metadata = {
  title: "Generation Studio",
};

export default async function StudioPage({ searchParams }: { searchParams: Promise<{ domain?: string }> }) {
  const params = await searchParams;
  const domain: DomainId = params.domain === "healthcare"
    ? "healthcare"
    : params.domain === "support"
      ? "support"
      : "invoices";
  return <StudioClient initialDomain={domain} />;
}
