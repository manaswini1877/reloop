// Admin screen showing campus-wide reported e-waste items with 5s polling.
import { useState, useEffect } from 'react';
import { getItems } from '../api.js';
import { UI } from '../i18n.js';

export default function AdminList({ onSelectItem }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);
  const [error, setError] = useState(null);

  // Poll getItems every 5 seconds; clean up interval on unmount
  useEffect(() => {
    let isMounted = true;

    const fetchItems = async () => {
      try {
        const data = await getItems();
        if (!isMounted) return;
        if (data && Array.isArray(data.items)) {
          // Ensure newest first by created_at timestamp
          const sorted = [...data.items].sort(
            (a, b) => new Date(b.created_at) - new Date(a.created_at)
          );
          setItems(sorted);
          setReconnecting(false);
          setError(null);
        }
      } catch (err) {
        if (!isMounted) return;
        console.error('Error fetching items feed:', err);
        // Keep showing existing items on transient poll failure and display reconnecting note
        setReconnecting(true);
        setItems((currentItems) => {
          if (currentItems.length === 0) {
            setError('Unable to load items feed.');
          }
          return currentItems;
        });
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchItems(); // Initial fetch
    const intervalId = setInterval(fetchItems, 5000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  // Format timestamp to readable time
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
        <div className="status-badge-row">
          {reconnecting ? (
            <div className="reconnecting-badge" role="status">
              <span className="reconnecting-dot"></span>
              <span>Reconnecting...</span>
            </div>
          ) : (
            <div className="poll-badge">
              <span className="pulse-dot"></span>
              <span>{UI.pollStatus}</span>
            </div>
          )}
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
                {/* Placeholder thumbnail box with camera/box icon */}
                <div className="item-row-thumbnail-box" aria-hidden="true">
                  <svg
                    className="thumbnail-icon"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                    <circle cx="12" cy="13" r="4" />
                  </svg>
                </div>

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
