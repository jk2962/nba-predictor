/**
 * NBA Player Performance Prediction - Main App
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import ThemeToggle from './components/ThemeToggle';
import HomePage from './pages/HomePage';
import PlayerDetailPage from './pages/PlayerDetailPage';
import ComparisonPage from './pages/ComparisonPage';
import DraftHelperPage from './pages/DraftHelperPage';
import BrowsePage from './pages/BrowsePage';
import './index.css';

function App() {
  return (
    <Router>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/browse" element={<BrowsePage />} />
            <Route path="/player/:playerId" element={<PlayerDetailPage />} />
            <Route path="/compare" element={<ComparisonPage />} />
            <Route path="/draft" element={<DraftHelperPage />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer style={{
          textAlign: 'center',
          padding: 'var(--space-lg)',
          borderTop: '1px solid var(--border-subtle)',
          color: 'var(--text-tertiary)',
          fontSize: '0.8125rem',
        }}>
          <p style={{ margin: 0 }}>NBA Player Performance Prediction • Powered by XGBoost</p>
        </footer>

        {/* Theme Toggle */}
        <ThemeToggle />
      </div>
    </Router>
  );
}

export default App;

