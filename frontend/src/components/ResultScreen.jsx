// Screen showing classification results, hazard alerts, and bilingual safe-handling steps.
import { useState } from 'react';
import { UI, SAFE_STEP_LANG, getSafeSteps } from '../i18n.js';

export default function ResultScreen({ item, onReportAnother, onViewAllItems }) {
  // Safe steps language toggle state ('en' vs 'te'). Default English.
  const [stepLang, setStepLang] = useState(SAFE_STEP_LANG.EN);

  if (!item) {
    return (
      <div className="screen-container">
        <p>No result selected.</p>
        <button type="button" className="btn btn-primary" onClick={onReportAnother}>
          {UI.reportAnotherBtn}
        </button>
      </div>
    );
  }

  const isHazard = item.route === 'hazard';
  const confidencePercent = Math.round((item.confidence || 0) * 100);
  const currentSteps = getSafeSteps(item, stepLang);

  // Determine route badge class
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
    <div className="screen-container result-screen">
      {/* Large RED banner for hazardous items */}
      {isHazard && (
        <div className="hazard-banner" role="alert">
          <div className="hazard-icon">🚨</div>
          <div className="hazard-text">
            <strong>{UI.hazardBanner}</strong>
            <p>Do not throw this in regular trash or standard bins. Follow handling instructions below.</p>
          </div>
        </div>
      )}

      {/* Main Result Card */}
      <div className={`result-card ${isHazard ? 'card-hazard' : ''}`}>
        {/* Item Header & Route Badge */}
        <div className="result-header">
          <div className="item-title-col">
            <span className="item-type-label">Detected Item</span>
            <h2 className="item-title">{item.item}</h2>
          </div>
          <div className="route-badge-wrapper">
            <span className={getBadgeClass(item.route)}>
              {item.route?.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Swollen Battery Tag */}
        {item.swollen_battery && (
          <div className="warning-pill">
            ⚠️ <strong>{UI.swollenWarning}</strong>
          </div>
        )}

        {/* Metadata Grid */}
        <div className="metadata-grid">
          <div className="metadata-box">
            <span className="metadata-label">{UI.conditionLabel}</span>
            <span className="metadata-value capitalize">{item.condition || 'N/A'}</span>
          </div>
          <div className="metadata-box">
            <span className="metadata-label">{UI.confidenceLabel}</span>
            <span className="metadata-value">{confidencePercent}%</span>
          </div>
          <div className="metadata-box">
            <span className="metadata-label">{UI.batteryRiskLabel}</span>
            <span className="metadata-value capitalize">{item.battery_risk || 'None'}</span>
          </div>
        </div>

        {/* Reason / Explanation */}
        <div className="reason-section">
          <h4 className="reason-heading">{UI.reasonLabel}</h4>
          <p className="reason-text">{item.reason}</p>
        </div>

        {/* Safe Handling Steps Section */}
        <div className={`safe-steps-box ${isHazard ? 'steps-hazard-box' : 'steps-standard-box'}`}>
          <div className="steps-header">
            <h3 className="steps-title">
              {isHazard ? '⚠️ ' : '📋 '}
              {UI.safeStepsTitle}
            </h3>

            {/* Language Toggle for Safe Steps ONLY */}
            <div className="lang-toggle-group" role="group" aria-label="Safe steps language toggle">
              <button
                type="button"
                className={`lang-btn ${stepLang === SAFE_STEP_LANG.EN ? 'active' : ''}`}
                onClick={() => setStepLang(SAFE_STEP_LANG.EN)}
              >
                EN
              </button>
              <button
                type="button"
                className={`lang-btn ${stepLang === SAFE_STEP_LANG.TE ? 'active' : ''}`}
                onClick={() => setStepLang(SAFE_STEP_LANG.TE)}
              >
                తెలుగు
              </button>
            </div>
          </div>

          <ol className="safe-steps-list">
            {currentSteps.map((step, idx) => (
              <li key={idx} className="safe-step-item">
                <span className="step-number">{idx + 1}</span>
                <span className="step-text">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="result-actions">
        <button
          type="button"
          className="btn btn-primary action-btn-full"
          onClick={onReportAnother}
        >
          {UI.reportAnotherBtn}
        </button>
        {onViewAllItems && (
          <button
            type="button"
            className="btn btn-secondary action-btn-full"
            onClick={onViewAllItems}
          >
            {UI.viewAllItemsBtn}
          </button>
        )}
      </div>
    </div>
  );
}
