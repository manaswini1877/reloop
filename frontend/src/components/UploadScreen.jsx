// Screen for students to capture or select a photo of e-waste and analyze it.
import { useState, useRef } from 'react';
import { getUploadUrl, uploadToS3, analyze } from '../api.js';
import { UI } from '../i18n.js';

export default function UploadScreen({ onAnalyzeSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  // Handle image selection from file picker or camera
  const handleFileChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setErrorMessage(null);
    }
  };

  // Trigger hidden file input click
  const handleOpenPicker = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Perform upload and analysis flow
  const handleAnalyze = async () => {
    if (!selectedFile) {
      setErrorMessage(UI.noPhotoSelected);
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      // Step 1: Request presigned upload URL
      const { upload_url, image_key } = await getUploadUrl(
        selectedFile.name,
        selectedFile.type || 'image/jpeg'
      );

      // Step 2: Upload file to storage
      await uploadToS3(upload_url, selectedFile);

      // Step 3: Call AI analyze endpoint
      const result = await analyze(image_key);

      // Success callback
      onAnalyzeSuccess(result);
    } catch (err) {
      console.error('Analysis error:', err);
      setErrorMessage(err.message || UI.analysisFailed);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="screen-container upload-screen">
      <div className="header-box">
        <h1 className="screen-title">{UI.uploadTitle}</h1>
        <p className="screen-subtitle">{UI.uploadDescription}</p>
      </div>

      {/* Hidden file input supporting camera capture on mobile */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        id="camera-file-input"
      />

      {/* Main Upload / Camera Area */}
      {!previewUrl ? (
        <div className="dropzone-area" onClick={handleOpenPicker}>
          <div className="camera-icon-bubble">📸</div>
          <button
            type="button"
            className="btn btn-primary big-action-btn"
            onClick={(e) => {
              e.stopPropagation();
              handleOpenPicker();
            }}
          >
            {UI.takePhoto}
          </button>
          <span className="dropzone-hint">Tap to take photo or choose from gallery</span>
        </div>
      ) : (
        <div className="preview-container">
          <div className="image-preview-wrapper">
            <img src={previewUrl} alt="E-waste preview" className="image-preview" />
          </div>

          <div className="preview-controls">
            <button
              type="button"
              className="btn btn-secondary change-photo-btn"
              onClick={handleOpenPicker}
              disabled={loading}
            >
              {UI.changePhoto}
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-card" role="status" aria-live="polite">
          <div className="spinner"></div>
          <h3 className="loading-title">{UI.analyzingTitle}</h3>
          <p className="loading-subtitle">{UI.analyzingSubtitle}</p>
        </div>
      )}

      {/* Error state with retry */}
      {errorMessage && !loading && (
        <div className="error-card" role="alert">
          <div className="error-icon">⚠️</div>
          <div className="error-text">
            <strong>{UI.errorTitle}</strong>
            <p>{errorMessage}</p>
          </div>
          <button
            type="button"
            className="btn btn-retry"
            onClick={handleAnalyze}
          >
            {UI.retryBtn}
          </button>
        </div>
      )}

      {/* Analyze Action Button */}
      {previewUrl && !loading && (
        <div className="action-button-row">
          <button
            type="button"
            className="btn btn-success big-analyze-btn"
            onClick={handleAnalyze}
          >
            {UI.analyzeBtn}
          </button>
        </div>
      )}
    </div>
  );
}
