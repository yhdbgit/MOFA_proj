# Staff Console Web

Placeholder for the web-based situation management console.

Expected stack:

- React.
- Tailwind CSS.

Expected screens later:

- Realtime chat/incident list.
- Incident detail.
- Chat transcript viewer.
- Agent result viewer.
- Official document draft review.

## Temporary E2E Test UI

This folder currently contains a minimal React/Vite test UI for backend flow verification.

Run:

```bash
npm install
npm run dev
```

Open:

```txt
http://localhost:5173
```

The Vite dev server proxies `/api` requests to Spring Boot on `http://localhost:8080`.
