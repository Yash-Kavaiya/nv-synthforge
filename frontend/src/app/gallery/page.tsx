import { Suspense } from "react";
import { GalleryClient } from "@/components/gallery-client";
import { Skeleton } from "@/components/ui";

export const metadata = {
  title: "Results Gallery",
  description: "Inspect and export synthetic invoice artifacts.",
};

export default function GalleryPage() {
  return (
    <Suspense fallback={<div className="gallery-grid" aria-label="Loading gallery">{Array.from({ length: 6 }, (_, index) => <Skeleton key={index} className="gallery-skeleton" />)}</div>}>
      <GalleryClient />
    </Suspense>
  );
}
