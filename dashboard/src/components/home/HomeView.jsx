import HeroSection from './HeroSection';
import LatestPreview from './LatestPreview';
import FeatureBento from './FeatureBento';

export default function HomeView() {
  return (
    <div id="view-home" className="w-full">
      <HeroSection>
        <LatestPreview />
      </HeroSection>
      <FeatureBento />
    </div>
  );
}
