// Utility functions for validating and resizing images on the client side before upload.

// Allowed image MIME types per contract
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/**
 * Validates whether the given file is an allowed image type (JPG, PNG, or WebP).
 * @param {File} file
 * @returns {boolean}
 */
export function isValidImageType(file) {
  if (!file || !file.type) return false;
  return ALLOWED_IMAGE_TYPES.includes(file.type.toLowerCase());
}

/**
 * Helper to convert canvas to a Blob with specific quality.
 * @param {HTMLCanvasElement} canvas
 * @param {number} quality
 * @returns {Promise<Blob>}
 */
function canvasToBlob(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Canvas toBlob conversion failed'));
        }
      },
      'image/jpeg',
      quality
    );
  });
}

/**
 * Resizes an image on the phone before upload:
 * - Scales the image so its longest side is at most 1280px while keeping aspect ratio.
 * - Exports as JPEG with quality 0.8.
 * - If still over 3.5 MB, progressively reduces quality (0.7, 0.6, 0.5) until under 3.5 MB.
 * 
 * @param {File} file - Selected image file
 * @returns {Promise<Blob>} - Resized JPEG Blob
 */
export async function resizeImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = async () => {
      URL.revokeObjectURL(objectUrl);
      try {
        let width = img.naturalWidth || img.width;
        let height = img.naturalHeight || img.height;
        const maxSide = 1280;

        // Scale down if longest side exceeds 1280px
        if (width > maxSide || height > maxSide) {
          if (width >= height) {
            height = Math.round((height * maxSide) / width);
            width = maxSide;
          } else {
            width = Math.round((width * maxSide) / height);
            height = maxSide;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('Unable to obtain canvas 2D rendering context');
        }

        // Draw image onto canvas
        ctx.drawImage(img, 0, 0, width, height);

        // Max file size: 3.5 MB (3.5 * 1024 * 1024 bytes)
        const MAX_SIZE_BYTES = 3.5 * 1024 * 1024;
        const qualities = [0.8, 0.7, 0.6, 0.5];
        let chosenBlob = null;

        for (const quality of qualities) {
          chosenBlob = await canvasToBlob(canvas, quality);
          // Stop as soon as the image fits under 3.5 MB
          if (chosenBlob.size <= MAX_SIZE_BYTES) {
            break;
          }
        }

        resolve(chosenBlob);
      } catch (err) {
        reject(err);
      }
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Failed to load image'));
    };

    img.src = objectUrl;
  });
}
