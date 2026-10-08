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

## Switching Between Mock and Real Mode

The frontend communicates through the standardized contract in `src/api.js`. You can toggle between **Mock Mode** (Phase 1 default) and **Real API Mode** using environment variables.

### 1. Mock Mode (Phase 1 Default)
In your `frontend/.env` file:
```env
VITE_USE_MOCK=true
VITE_API_BASE_URL=
```
- In Mock Mode, no backend or AWS connection is required.
- Simulates realistic 1.5-second scan latency.
- In-memory list updates dynamically when new items are analyzed.
- Admin list polls and reflects newly analyzed items automatically every 5 seconds.

### 2. Real API Mode (Phase 2)
In your `frontend/.env` file:
```env
VITE_USE_MOCK=false
VITE_API_BASE_URL=https://your-api-gateway-or-server.com
```
- Calls the live backend endpoints:
  - `POST /upload-url` (presigned S3 upload URL)
  - `PUT <upload_url>` (direct binary upload)
  - `POST /analyze` (AI classification)
  - `GET /items` (campus items feed)
  - `GET /items/{id}` (item detail)

---

## Features
- **Mobile-First UX**: Optimized for mobile screens (e.g. 375px width) with touch targets >= 44px.
- **Hazard Alerts**: Instant red banner (`HAZARD - do not put in a bin`) and highlighted safe-handling callout for swollen batteries and high-risk electronics.
- **Bilingual Safe Handling**: One-tap toggle between English and Telugu for safe-handling steps.
- **Campus Stream (Admin Feed)**: Auto-polling list updating every 5 seconds without manual page reload.
