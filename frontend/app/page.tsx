import Hero from "@/components/Hero";
import Marquee from "@/components/Marquee";
import CreatorSection from "@/components/CreatorSection";
import FeatureGrid from "@/components/FeatureGrid";
import LibrarySection from "@/components/LibrarySection";

export default function Page() {
  return (
    <>
      <div id="dashboard">
        <Hero />
      </div>
      <Marquee />
      <CreatorSection />
      <FeatureGrid />
      <LibrarySection />
    </>
  );
}
