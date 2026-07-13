import type { Metadata } from "next";
import { BenchmarkClient } from "@/components/benchmark-client";

export const metadata: Metadata = {
  title: "Benchmarks",
  description: "Measure deterministic quality, throughput, and document-generation latency.",
};

export default function BenchmarksPage() {
  return <BenchmarkClient />;
}
