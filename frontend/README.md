# ReLoop Frontend

ReLoop is a mobile-first e-waste routing web application for university campuses. It helps hostel students and campus staff determine the safest next life for any electronic waste item (**hazard**, **repair**, or **recycle**), detects dangerous swollen batteries, and displays bilingual safe-handling steps in English and Telugu.

---

## Tech Stack
- **Framework**: React 19 + Vite
- **Styling**: Plain CSS (No Tailwind, mobile-first, Telugu font stack, min 44px tap targets)
- **Language**: JavaScript (ES modules)
- **Routing**: Zero-dependency state navigation (Report, Result, Items)

---

## Installation

Ensure you are inside the `frontend` directory:

```bash
cd frontend
npm install
```

---

## Running the Development Server

To start the Vite development server locally:

```bash
npm run dev
```

The application will be accessible at `http://localhost:5173/` (or the port specified by Vite).

---

## Switching Between Mock Mode and Real Mode

The frontend communicates through the standardized contract in `src/api.js`. You can toggle between **Mock Mode** (local testing) and **Real Mode** (live AWS backend) using environment variables.

### 1. Mock Mode (Local Fallback)
In your `frontend/.env` file:
```env
VITE_USE_MOCK=true
VITE_API_URL=
```
- No AWS backend connection or cloud network access required.
- Simulates realistic 1.5-second scan latency.
- In-memory list updates dynamically when new items are analyzed.
- Admin list polls every 5 seconds and immediately reflects newly analyzed items.
- Perfect for offline development, local demos, and fallback testing.

### 2. Real Mode (Live Backend)
In your `frontend/.env` file:
```env
VITE_USE_MOCK=false
VITE_API_URL=https://mn67sloi6c.execute-api.us-east-1.amazonaws.com/prod
```
- Connects directly to the live AWS API Gateway and S3 bucket:
  - `POST /upload-url`: requests presigned S3 upload URL for `photo.jpg` (`image/jpeg`).
  - `PUT <upload_url>`: uploads the client-resized JPEG blob (under 3.5 MB, max 1280px) with only `Content-Type: image/jpeg`.
  - `POST /analyze`: submits `image_key` for AI classification and DynamoDB persistence.
  - `GET /items`: auto-polls the latest campus e-waste reports every 5 seconds.
  - `GET /items/{id}`: retrieves individual item detail.
- Client-side error handling:
  - If S3 upload fails, offers an immediate retry from the upload step.
  - If analysis fails (e.g., HTTP 502 or network error), offers a retry directly from the analyze step using the already-uploaded image key.
  - If background polling encounters a transient network drop, shows a subtle "Reconnecting..." status while keeping the existing items list visible without disruption.

---

## Features
- **Mobile-First UX**: Optimized for mobile touch devices (min 44px tap targets, responsive layout).
- **Client-Side Image Optimization**: Pre-upload downscaling to max 1280px and progressive JPEG quality reduction (0.8 -> 0.7 -> 0.6 -> 0.5) ensuring payloads stay safely under 3.5 MB.
- **Hazard Alerts**: Instant red banner (`HAZARD - do not put in a bin`) and highlighted safe-handling callout for swollen batteries and high-risk electronics.
- **Bilingual Safe Handling**: One-tap toggle between English and Telugu for safe-handling steps.
- **Campus Stream (Admin Feed)**: Auto-polling list updating every 5 seconds without manual page reload, with graceful transient reconnect handling and item placeholder fallbacks.
