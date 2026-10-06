# Tennis Explore — Full Stack

Tennis intelligence platform: structured rankings (PostgreSQL + FastAPI) + unstructured RAG (FAISS + BM25 + reranker + Ollama) + modern React frontend.

## Stack

**Backend:** Python, FastAPI, Uvicorn, PostgreSQL 16, `psycopg2`, `PyJWT` (24h access + 7d refresh), `passlib[bcrypt]==4.0.1`, `python-dotenv`  
**Unstructured:** `sentence-transformers/all-MiniLM-L6-v2`, `faiss-cpu`, `rank-bm25`, `BAAI/bge-reranker-base`, `pypdf`, `python-pptx`  
**Frontend:** React 18, React Router 7, Vite 6, Tailwind 3, shadcn/ui (Radix), Zustand (auth store), TanStack Query, Formik + Yup, Axios (interceptors + auto refresh), Framer Motion, Lucide + Material Symbols, Inter font throughout

## Quick Start

```bash
git clone <repo-url>
cd 735-Tennis-Explore
# see SETUP.md for detailed per-OS instructions (macOS/Linux/Windows/Docker)
```

**Backend:**
```bash
cd 735-Tennis-Explore
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
# create backend/.env from backend/.env.example (see SETUP.md)
psql -d tennis_rankings_v2 -f backend/structured_data/sql/01_create_schema.sql
psql -d tennis_rankings_v2 -f backend/auth/sql/01_create_users.sql
python -m uvicorn backend.structured_data.api:app --host 0.0.0.0 --port 8000 --reload
# http://localhost:8000/health , /docs
```

**Frontend:**
```bash
cd frontend
npm install
# create frontend/.env -> VITE_API_URL=http://localhost:8000
npm run dev -- --host 0.0.0.0 --port 5173
# http://localhost:5173 -> login admin/admin123 (admin) or coach/coach123 (coach)
npm run build && npm run preview -- --port 4173
```

## Roles & Auth

- `role` is `VARCHAR(20) DEFAULT 'coach'` — only `admin` / `coach` (app validates, no DB enum). First seeded user is `admin`.
- Seeded: `admin@tennisexplore.au / admin123` (admin), `coach@tennisexplore.au / coach123` (coach)
- JWT `HS256`: access 24h `JWT_EXPIRE_HOURS`, refresh 7d `JWT_REFRESH_EXPIRE_DAYS` via `POST /auth/refresh {refresh_token}`. Axios auto-retries 401 with refresh queue.
- `GET /auth/me`, `PUT /auth/me/password` (self only, needs current password), `GET/POST/PUT/DELETE /auth/users` (admin only, cannot self-delete), `POST /auth/login` returns `access_token` + `refresh_token`.

## Frontend Highlights

- **State:** Zustand `persist` (`tennis-explore-auth`) + `AuthProvider` validates `GET /auth/me` on refresh, `useAuth` hook.
- **Data:** TanStack Query `useUsers`, `useCreateUser`, etc. (`src/hooks/use-users.js`) with `invalidateQueries`, `QueryClientProvider` in `App.jsx`.
- **Forms:** Formik + Yup (`src/lib/validations.js`: `loginSchema`, `createUserSchema`, `updateUserSchema`, `changePasswordSchema`) on login, admin create/edit, header change-password dialog.
- **API:** Axios instance `src/lib/axios.js` with request (attach `Bearer`) + response (401 → `POST /auth/refresh` → retry queue) handlers. Reusable `src/lib/query-client.js`, `src/components/shared/form-field.jsx`.
- **Routing:** `BrowserRouter` + `ProtectedRoute` (loading skeleton) + `RoleGuard allowedRoles` for `/media-library`, `/ai-chatbot` (`admin,coach`), `/users` (`admin` only). Sidebar shows `User Management` only for admin.
- **Lazy + Skeleton:** `React.lazy` + `Suspense fallback={<PageSkeleton/>}` in `App.jsx` (Vite `manualChunks` splits `react-vendor`, `router`, `query`, `form`, `axios`, `radix`, `motion`, etc., `chunkSizeWarningLimit:600` → no warning).
- **User account:** Header `h-[84px]` pill `bg-primary/10 border-2 border-primary/30 shadow-md`, `h-12 w-12` avatar with initials `text-[16px]` (`getInitials`), name `text-[15px] font-extrabold`, role `text-[13px] uppercase`, dropdown `w-72`. No image, initials only.
- **Font:** `Inter` everywhere (`index.css` `font-sans`, `tailwind.config.js`, `TennisExploreHero` + `login` removed `Playfair Display`), `material-symbols-outlined` for icons.

## Project Structure

```
735-Tennis-Explore/
├── backend/
│   ├── structured_data/api.py, database.py, queries.py, structured_chat.py, sql/*.sql
│   ├── auth/sql/01_create_users.sql, utils.py (JWT 24h/7d), deps.py (require_admin), router.py (login, refresh, me, me/password, users CRUD)
│   ├── documents_v2/{00_ingestion..10_database}
│   ├── requirements.txt, .env.example
│   └── auth/tests (via curl)
├── frontend/
│   ├── src/
│   │   ├── store/auth-store.js (zustand)
│   │   ├── lib/axios.js, query-client.js, validations.js, utils.js
│   │   ├── hooks/use-auth.js, use-users.js
│   │   ├── components/{layout/{app-layout,header,sidebar,protected-route,role-guard}, shared/{form-field}, ui/{skeleton,dialog,button,...}}
│   │   ├── pages/{TennisExploreHero,login,media-library,ai-chatbot,admin-users}
│   │   ├── App.jsx (lazy, QueryClientProvider, RoleGuard)
│   │   └── index.css (Inter)
│   ├── vite.config.js (manualChunks, chunkSizeWarningLimit:600, /auth proxy)
│   └── .env (VITE_API_URL)
└── SETUP.md (per-OS runbook)
```

See `SETUP.md` for per-OS install, env, migrate, and verify steps. `frontend/README.md` for design tokens.
