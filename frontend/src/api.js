// API client for ReLoop.
// Reads VITE_USE_MOCK and VITE_API_BASE_URL.
// Defaults to mock mode (Phase 1) with an in-memory list and simulated delays.

import { MOCK_ITEMS } from './mockData.js';

// In-memory list initialized with the 4 realistic mock items
let inMemoryItems = [...MOCK_ITEMS];
let mockAnalyzeIndex = 0;

// Helper to check whether we should use mock data
const isMockMode = () => {
  const envVal = import.meta?.env?.VITE_USE_MOCK;
  return envVal === undefined || envVal === null || envVal === 'true' || envVal === true;
};

// Helper to get base API URL
const getBaseUrl = () => {
  return import.meta?.env?.VITE_API_BASE_URL || '';
};

// Helper for simulated delay
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Request a presigned S3 upload URL.
 * Contract: POST /upload-url body {"filename":"x.jpg","content_type":"image/jpeg"}
 * Returns: {"upload_url":"...","image_key":"uploads/<uuid>.jpg"}
 */
export async function getUploadUrl(filename, contentType = 'image/jpeg') {
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

  // TODO: Real mode is untested in Phase 1.
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
 * Upload the binary file to the presigned S3 URL.
 */
export async function uploadToS3(uploadUrl, file) {
  if (isMockMode()) {
    await delay(300);
    return true;
  }

  // TODO: Real mode is untested in Phase 1.
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type || 'image/jpeg'
    },
    body: file
  });

  if (!response.ok) {
    throw new Error(`Failed to upload to S3: ${response.status}`);
  }

  return true;
}

/**
 * Submit an uploaded image for e-waste AI classification.
 * Contract: POST /analyze body {"image_key":"uploads/<uuid>.jpg"} -> Item
 * Mock mode: 1.5 second fake delay, cycles next mock item, prepends to list so getItems shows it.
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

  // TODO: Real mode is untested in Phase 1.
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
      // Fallback to HTTP status text
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
    // Instant or light delay for responsive polling
    return { items: [...inMemoryItems] };
  }

  // TODO: Real mode is untested in Phase 1.
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

  // TODO: Real mode is untested in Phase 1.
  const response = await fetch(`${getBaseUrl()}/items/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch item: ${response.status}`);
  }

  return await response.json();
}
