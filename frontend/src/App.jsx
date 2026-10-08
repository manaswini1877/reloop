// Main Application shell with simple state-based navigation and mobile bottom bar.
import { useState } from 'react';
import UploadScreen from './components/UploadScreen.jsx';
import ResultScreen from './components/ResultScreen.jsx';
import AdminList from './components/AdminList.jsx';
import { UI } from './i18n.js';

export default function App() {
  // Navigation states: 'report' | 'result' | 'items'
  const [currentScreen, setCurrentScreen] = useState('report');
  const [activeItem, setActiveItem] = useState(null);

  // When an item is analyzed, navigate to Result screen
  const handleAnalyzeSuccess = (item) => {
    setActiveItem(item);
    setCurrentScreen('result');
  };

  // When an item is clicked in the Admin List, navigate to Result screen
  const handleSelectItem = (item) => {
    setActiveItem(item);
    setCurrentScreen('result');
  };

  // Return to report flow
  const handleReportAnother = () => {
    setActiveItem(null);
    setCurrentScreen('report');
  };

  // View admin items list
  const handleViewAllItems = () => {
    setCurrentScreen('items');
  };

  return (
    <div className="app-layout">
      {/* Top App Header */}
      <header className="app-header">
        <div className="brand-wrap" onClick={handleReportAnother} role="button" tabIndex={0}>
          <span className="brand-logo" aria-hidden="true">♻️</span>
          <div className="brand-meta">
            <span className="brand-name">{UI.appName}</span>
            <span className="brand-tagline">{UI.tagline}</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="app-content">
        {currentScreen === 'report' && (
          <UploadScreen onAnalyzeSuccess={handleAnalyzeSuccess} />
        )}

        {currentScreen === 'result' && (
          <ResultScreen
            item={activeItem}
            onReportAnother={handleReportAnother}
            onViewAllItems={handleViewAllItems}
          />
        )}

        {currentScreen === 'items' && (
          <AdminList onSelectItem={handleSelectItem} />
        )}
      </main>

      {/* Bottom Navigation (Report, Items) */}
      <nav className="bottom-nav" aria-label="Main Navigation">
        <button
          type="button"
          className={`nav-tab ${currentScreen === 'report' ? 'active' : ''}`}
          onClick={() => setCurrentScreen('report')}
          aria-current={currentScreen === 'report' ? 'page' : undefined}
        >
          <span className="nav-icon" aria-hidden="true">📷</span>
          <span className="nav-label">{UI.navReport}</span>
        </button>

        <button
          type="button"
          className={`nav-tab ${currentScreen === 'items' ? 'active' : ''}`}
          onClick={() => setCurrentScreen('items')}
          aria-current={currentScreen === 'items' ? 'page' : undefined}
        >
          <span className="nav-icon" aria-hidden="true">📋</span>
          <span className="nav-label">{UI.navItems}</span>
        </button>
      </nav>
    </div>
  );
}
