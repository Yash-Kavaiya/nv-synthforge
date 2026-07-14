import type { Metadata } from "next";
import { OCRBenchClient } from "@/components/ocr-bench-client";

export const metadata: Metadata = {
  title: "OCR Structure Benchmark",
  description: "Score OCR/document models against synthetic invoice JSON ground truth and PDF/image packs.",
};

export default function OCRPage() {
  return <OCRBenchClient />;
}
