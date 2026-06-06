import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { AppProvider } from './context/AppContext';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import HomeView from './components/home/HomeView';
import FeedView from './components/feed/FeedView';
import SavedView from './components/feed/SavedView';
import ArchitectureView from './components/health/ArchitectureView';
import ResearchView from './components/research/ResearchView';
import SourcesView from './components/sources/SourcesView';
import DetailDrawer from './components/drawer/DetailDrawer';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function AppContent() {
  return (
    <div className="min-h-screen bg-surface-base text-on-surface font-body-md flex flex-col">
      <ScrollToTop />
      <Navbar />
      <main className="flex-grow pt-16">
        <Routes>
          <Route path="/" element={<HomeView />} />
          <Route path="/feed" element={<FeedView />} />
          <Route path="/saved" element={<SavedView />} />
          <Route path="/health" element={<ArchitectureView />} />
          <Route path="/terminal" element={<ResearchView />} />
          <Route path="/sources" element={<SourcesView />} />
        </Routes>
      </main>
      <Footer />
      <DetailDrawer />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Router>
        <AppContent />
      </Router>
    </AppProvider>
  );
}
