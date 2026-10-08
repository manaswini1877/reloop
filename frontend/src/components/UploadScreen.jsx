// Screen for students to capture or select a photo of e-waste and analyze it.
import { useState, useRef } from 'react';
import { getUploadUrl, uploadToS3, analyze } from '../api.js';
import { isValidImageType, resizeImage } from '../imageUtils.js';
import { UI } from '../i18n.js';

export default function UploadScreen({ onAnalyzeSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('Uploading photo...');
  const [errorMessage, setErrorMessage] = useState(null);
  // Track uploaded S3 key to avoid re-uploading if only the analyze step failed
  const [uploadedKey, setUploadedKey] = useState(null);
  const fileInputRef = useRef(null);

  // Handle image selection from file picker or camera
  const handleFileChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      if (!isValidImageType(file)) {
        setErrorMessage('Please choose a JPG, PNG or WebP photo');
        setSelectedFile(null);
        setPreviewUrl(null);
        setUploadedKey(null);
        return;
      }

      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setErrorMessage(null);
      setUploadedKey(null);
    }
  };

  // Trigger hidden file input click
  const handleOpenPicker = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Perform upload and analysis flow with retry support
  const handleAnalyze = async (resumeAnalyzeOnly = false) => {
    if (!selectedFile) {
      setErrorMessage('Please choose a JPG, PNG or WebP photo');
      return;
    }

    if (!isValidImageType(selectedFile)) {
      setErrorMessage('Please choose a JPG, PNG or WebP photo');
      return;
    }

    setErrorMessage(null);
    setLoading(true);

    try {
      let imageKey = uploadedKey;

      // Step 1: Resize and upload (skip if already successfully uploaded)
      if (!resumeAnalyzeOnly || !imageKey) {
        setLoadingStep('Uploading photo...');

        // Resize image on device (max 1280px longest side, <= 3.5MB JPEG)
        let resizedBlob;
        try {
          resizedBlob = await resizeImage(selectedFile);
        } catch {
          resizedBlob = selectedFile;
        }

        // Request presigned S3 upload URL
        let uploadData;
        try {
          uploadData = await getUploadUrl('photo.jpg', 'image/jpeg');
        } catch (err) {
          console.error('Upload URL request failed:', err);
          throw new Error('UPLOAD_FAILED');
        }

        // Upload to S3 using ONLY Content-Type: image/jpeg header
        try {
          await uploadToS3(uploadData.upload_url, resizedBlob);
        } catch (err) {
          console.error('S3 PUT failed:', err);
          throw new Error('UPLOAD_FAILED');
        }

        imageKey = uploadData.image_key;
        setUploadedKey(imageKey);
      }

      // Step 2: Submit for AI classification
      setLoadingStep('Analyzing...');
      let result;
      try {
        result = await analyze(imageKey);
      } catch (err) {
        console.error('Analyze request failed:', err);
        throw new Error('ANALYZE_FAILED');
      }

      // Successfully finished
      setUploadedKey(null);
      onAnalyzeSuccess(result, previewUrl);
    } catch (err) {
      // Friendly, non-technical error messages
      if (err.message === 'UPLOAD_FAILED') {
        setErrorMessage('Upload failed. Check your connection and try again.');
      } else {
        setErrorMessage('We could not analyze this photo. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle retry: resume from analyze step if upload already succeeded, otherwise restart
  const handleRetry = () => {
    const shouldResumeAnalyze = Boolean(uploadedKey);
    handleAnalyze(shouldResumeAnalyze);
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
        accept="image/jpeg,image/png,image/webp"
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

      {/* Loading State with step indicators */}
      {loading && (
        <div className="loading-card" role="status" aria-live="polite">
          <div className="spinner"></div>
          <h3 className="loading-title">{loadingStep}</h3>
          <p className="loading-subtitle">{UI.analyzingSubtitle}</p>
        </div>
      )}

      {/* Error state with retry */}
      {errorMessage && !loading && (
        <div className="error-card" role="alert">
          <div className="error-icon">⚠️</div>
          <div className="error-text">
            <strong>{UI.errorTitle || 'Notice'}</strong>
            <p>{errorMessage}</p>
          </div>
          <button
            type="button"
            className="btn btn-retry"
            onClick={handleRetry}
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
            onClick={() => handleAnalyze(false)}
          >
            {UI.analyzeBtn}
          </button>
        </div>
      )}
    </div>
  );
}
