// API client for ReLoop.
// Reads VITE_USE_MOCK and VITE_API_URL.
// Supports both Real Mode (Phase 2 backend) and Mock Mode (fallback with in-memory store).

import { MOCK_ITEMS } from './mockData.js';

// In-memory list initialized with realistic mock items for mock mode
let inMemoryItems = [...MOCK_ITEMS];
let mockAnalyzeIndex = 0;

// Helper to check whether we should use mock data (defaults to true if unset)
export const isMockMode = () => {
  const envVal = import.meta?.env?.VITE_USE_MOCK;
  if (envVal === 'false' || envVal === false) {
    return false;
  }
  return true;
};

// Helper to get base API URL with trailing slash stripped
export const getBaseUrl = () => {
  const url = import.meta?.env?.VITE_API_URL || '';
  return url.replace(/\/+$/, '');
};

// Helper for simulated delay in mock mode
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Request a presigned S3 upload URL.
 * Contract: POST /upload-url body {"filename":"photo.jpg","content_type":"image/jpeg"}
 * Returns: {"upload_url":"...","image_key":"uploads/<uuid>.jpg"}
 */
export async function getUploadUrl(filename = 'photo.jpg', contentType = 'image/jpeg') {
  if (isMockMode()) {
    await delay(300);
    const mockUuid = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `mock-${Date.now()}`;
    return {
      upload_url: `https://mock-s3-upload.local/${mockUuid}`,
      image_key: `uploads/${mockUuid}.jpg`
    };
  }

  const response = await fetch(`${getBaseUrl()}/upload-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, content_type: contentType })
  });

  if (!response.ok) {
    throw new Error(`Failed to get upload URL: ${response.status}`);
  }

  return await response.json();
}

/**
 * Upload the binary blob to the presigned S3 URL.
 * Uses ONLY Content-Type: image/jpeg header per contract (no Auth or extra headers).
 */
export async function uploadToS3(uploadUrl, blob) {
  if (isMockMode()) {
    await delay(300);
    return true;
  }

  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': 'image/jpeg'
    },
    body: blob
  });

  if (!response.ok) {
    throw new Error(`Failed to upload to S3: ${response.status}`);
  }

  return true;
}

/**
 * Submit an uploaded image key for e-waste AI classification.
 * Contract: POST /analyze body {"image_key":"uploads/<uuid>.jpg"} -> Item
 */
export async function analyze(imageKey) {
  if (isMockMode()) {
    // 1.5 second fake delay for realistic scanning experience
    await delay(1500);

    const template = MOCK_ITEMS[mockAnalyzeIndex % MOCK_ITEMS.length];
    mockAnalyzeIndex++;

    const newUuid = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `item-${Date.now()}`;

    const analyzedItem = {
      ...template,
      id: newUuid,
      image_key: imageKey || `uploads/${newUuid}.jpg`,
      created_at: new Date().toISOString(),
      status: 'reported'
    };

    // Prepend to in-memory list (newest first)
    inMemoryItems = [analyzedItem, ...inMemoryItems];

    return analyzedItem;
  }

  const response = await fetch(`${getBaseUrl()}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_key: imageKey })
  });

  if (!response.ok) {
    let errorDetail = `Analysis failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.error) {
        errorDetail = errJson.error;
      }
    } catch {
      // Fallback to default message
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Fetch all reported items.
 * Contract: GET /items -> {"items":[Item,...]} newest first
 */
export async function getItems() {
  if (isMockMode()) {
    return { items: [...inMemoryItems] };
  }

  const response = await fetch(`${getBaseUrl()}/items`);
  if (!response.ok) {
    throw new Error(`Failed to fetch items: ${response.status}`);
  }

  return await response.json();
}

/**
 * Fetch a single item by ID.
 * Contract: GET /items/{id} -> Item
 */
export async function getItem(id) {
  if (isMockMode()) {
    const found = inMemoryItems.find((item) => item.id === id);
    if (!found) {
      throw new Error(`Item ${id} not found`);
    }
    return found;
  }

  const response = await fetch(`${getBaseUrl()}/items/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch item: ${response.status}`);
  }

  return await response.json();
}
