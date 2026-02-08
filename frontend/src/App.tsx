/**
 * NBA Player Performance Prediction - Main App
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import PlayerDetailPage from './pages/PlayerDetailPage';
import ComparisonPage from './pages/ComparisonPage';
import DraftHelperPage from './pages/DraftHelperPage';
import './index.css';

function App() {
  return (
    <Router>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/player/:playerId" element={<PlayerDetailPage />} />
            <Route path="/compare" element={<ComparisonPage />} />
            <Route path="/draft" element={<DraftHelperPage />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer style={{
          textAlign: 'center',
          padding: '1.5rem',
          borderTop: '1px solid rgba(255,255,255,0.1)',
          color: 'var(--color-text-muted)',
          fontSize: '0.85rem',
        }}>
          <p>NBA Player Performance Prediction MVP • Powered by XGBoost</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
