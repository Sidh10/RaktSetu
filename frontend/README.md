# frontend

React 18 + Vite 5 UI for the RaktSetu prototype (ADR-005). JavaScript, no PWA features.
Layout and colours come from the v3 dashboard mock-up (`dashboard_v3/build_dashboard_v3.py`).

```bash
npm install          # once (make setup-web)
npm run dev          # http://localhost:5173, proxies /api to the API on :8000 (make web)
npm run build        # dist/, served by FastAPI at http://localhost:8000 (make build-web; restart make api)
```

Pages (hash routes): `#/board` coordinator board and transfer cards, `#/centre` staff view, `#/trust` report
trust, `#/audit` audit log, `#/finder` public finder. Every page shows the banner "Simulated data · mock channel ·
not clinically validated"; the role switcher is labelled "Demo users · not real authentication".
