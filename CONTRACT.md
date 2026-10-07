\# ReLoop CONTRACT (all three members must match this exactly)



\## API (JSON, CORS enabled)



\### POST /upload-url

Body: {"filename":"x.jpg","content\_type":"image/jpeg"}

Returns: {"upload\_url":"<presigned S3 PUT url>","image\_key":"uploads/<uuid>.jpg"}



\### POST /analyze

Body: {"image\_key":"uploads/<uuid>.jpg"}

Returns: the Item object below (also saved in DynamoDB)



\### GET /items

Returns: {"items":\[Item, ...]} newest first



\### GET /items/{id}

Returns: Item



\## Item object

{

&#x20; "id": "uuid",

&#x20; "image\_key": "uploads/<uuid>.jpg",

&#x20; "created\_at": "ISO-8601 UTC",

&#x20; "item": "power bank",

&#x20; "condition": "damaged",        // good | worn | damaged

&#x20; "battery\_risk": "high",        // none | low | medium | high

&#x20; "swollen\_battery": true,

&#x20; "route": "hazard",             // hazard | repair | recycle

&#x20; "confidence": 0.82,            // 0 to 1

&#x20; "reason": "Battery casing looks bulged",

&#x20; "safe\_steps\_en": \["Keep away from heat", "Do not put in a bin", "Hand over to campus e-waste staff"],

&#x20; "safe\_steps\_te": \["<same 3 steps in Telugu>"],

&#x20; "status": "reported"

}



\## Rules

\- The AI model returns only the analysis fields. The backend adds id, image\_key, created\_at and status.

\- The model must return strict JSON only.

\- Route priority: hazard > repair > recycle.

\- If confidence is below 0.6 and a battery is visible, route is "hazard".

\- If the model output is invalid or Bedrock fails: return route "hazard" if a battery might be involved, otherwise {"error":"..."} with HTTP 502. Never crash.

\- Bedrock model ID comes from env var BEDROCK\_MODEL\_ID (never hardcoded).

\- Admin list polls GET /items every 5 seconds.



\## Folders

\- frontend/ (Member C)

\- backend/ (Member B)

\- ai/ (Member A)

