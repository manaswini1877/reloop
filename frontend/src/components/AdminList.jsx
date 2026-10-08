// Admin screen showing campus-wide reported e-waste items with 5s polling.
import { useState, useEffect } from 'react';
import { getItems } from '../api.js';
import { UI } from '../i18n.js';

export default function AdminList({ onSelectItem }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Function to fetch current items from API
  const fetchItems = async () => {
    try {
      const data = await getItems();
      if (data && Array.isArray(data.items)) {
        // Ensure newest first by created_at timestamp
        const sorted = [...data.items].sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at)
        );
        setItems(sorted);
        setError(null);
      }
    } catch (err) {
      console.error('Error fetching items:', err);
      setError('Unable to load items.');
    } finally {
      setLoading(false);
    }
  };

  // Poll getItems every 5 seconds; clean up interval on unmount
  useEffect(() => {
    fetchItems(); // Initial fetch

    const intervalId = setInterval(() => {
      fetchItems();
    }, 5000);

    return () => {
      clearInterval(intervalId);
    };
  }, []);

  // Format timestamp to user-friendly readable format
  const formatTime = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const getBadgeClass = (route) => {
    switch (route) {
      case 'hazard':
        return 'badge badge-hazard';
      case 'repair':
        return 'badge badge-repair';
      case 'recycle':
        return 'badge badge-recycle';
      default:
        return 'badge';
    }
  };

  return (
    <div className="screen-container admin-screen">
      <div className="header-box">
        <h1 className="screen-title">{UI.adminTitle}</h1>
        <p className="screen-subtitle">{UI.adminSubtitle}</p>
        <div className="poll-badge">
          <span className="pulse-dot"></span>
          <span>{UI.pollStatus}</span>
        </div>
      </div>

      <p className="admin-hint">{UI.tapToView}</p>

      {loading && items.length === 0 ? (
        <div className="loading-card">
          <div className="spinner"></div>
          <p>Loading items feed...</p>
        </div>
      ) : error && items.length === 0 ? (
        <div className="error-card">
          <p>{error}</p>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-card">
          <p>{UI.emptyList}</p>
        </div>
      ) : (
        <div className="item-list" role="list">
          {items.map((item) => {
            const isHazard = item.route === 'hazard';
            return (
              <div
                key={item.id}
                role="listitem"
                tabIndex={0}
                className={`item-row ${isHazard ? 'item-row-hazard' : ''}`}
                onClick={() => onSelectItem(item)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectItem(item);
                  }
                }}
              >
                <div className="item-row-info">
                  <div className="item-row-name-wrap">
                    {isHazard && <span className="hazard-warning-icon" title="Hazardous">⚠️</span>}
                    <strong className="item-row-name">{item.item}</strong>
                  </div>
                  <div className="item-row-meta">
                    <span className="item-row-condition capitalize">{item.condition}</span>
                    <span className="item-row-dot">•</span>
                    <span className="item-row-time">{formatTime(item.created_at)}</span>
                  </div>
                </div>

                <div className="item-row-badge-wrap">
                  <span className={getBadgeClass(item.route)}>
                    {item.route?.toUpperCase()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
