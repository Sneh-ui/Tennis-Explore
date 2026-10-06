# Tennis-Explore Dashboard

A professional React.js application for tennis analytics, built with **Vite**, **React Router**, **Tailwind CSS**, **shadcn/ui**, **Zustand**, **TanStack Query**, **Formik/Yup**, **Axios**.

## Project Structure

```
src/
├── store/
│   └── auth-store.js          # Zustand persist (tennis-explore-auth) + login/validateSession
├── lib/
│   ├── axios.js               # Axios instance + request/response interceptors + auto refresh (7d)
│   ├── query-client.js        # TanStack QueryClient (2m stale)
│   ├── validations.js         # Yup schemas: login, create/update user, change password
│   ├── utils.js               # cn() helper
│   └── pending-query.js, crypto.js
├── hooks/
│   ├── use-auth.js            # wraps Zustand store
│   └── use-users.js           # useUsers, useCreateUser, useUpdateUser, useDeleteUser, useUpdatePassword (tanstack)
├── components/
│   ├── layout/                # App shell
│   │   ├── app-layout.jsx
│   │   ├── header.jsx         # h-[84px] pill, h-12 w-12 initials, change-password Dialog (Formik/Yup)
│   │   ├── sidebar.jsx        # shows User Management only for admin
│   │   ├── protected-route.jsx
│   │   └── role-guard.jsx     # allowedRoles check + Access Denied
│   ├── shared/
│   │   ├── form-field.jsx     # reusable FormField/FormInput/FormSelect (Formik + accessibility)
│   │   ├── data-table.jsx
│   │   ├── icon.jsx
│   │   ├── page-header.jsx
│   │   └── ...
│   └── ui/                    # shadcn/ui + custom
│       ├── skeleton.jsx       # Skeleton, TableSkeleton, PageSkeleton, CardSkeleton
│       ├── dialog.jsx
│       ├── button.jsx, card.jsx, input.jsx, select.jsx, ...
│       └── avatar.jsx, etc.
├── pages/
│   ├── TennisExploreHero.jsx  # Inter only, initials, lazy
│   ├── login.jsx              # Formik + Yup, demo admin/coach fills
│   ├── admin-users.jsx        # TanStack Query + Formik/Yup, TableSkeleton
│   ├── media-library.jsx
│   ├── ai-chatbot.jsx
│   ├── dashboard.jsx, data-portal.jsx, archive.jsx
│   └── index.js
├── App.jsx                    # QueryClientProvider, lazy + Suspense fallback={<PageSkeleton/>}, RoleGuard for /media-library, /ai-chatbot (admin,coach) and /users (admin)
├── main.jsx
└── index.css                  # Inter font-sans throughout
```

## Getting Started

```bash
npm install # installs zustand, formik, yup, @tanstack/react-query, axios, etc.
npm run dev -- --host 0.0.0.0 --port 5173 # http://localhost:5173
npm run build # vite build with manualChunks (react-vendor, router, query, form, axios, radix, motion) + chunkSizeWarningLimit:600
npm run preview -- --host 0.0.0.0 --port 4173
```

Env: `VITE_API_URL=http://localhost:8000` (see `vite.config.js` proxy `/auth`).

## Roles

- `admin` → can manage users (`/users`), plus media/ai
- `coach` → can access `media-library`, `ai-chatbot` only
- `RoleGuard` + `Sidebar` + `AdminUsersPage` enforce, `ProtectedRoute` validates `GET /auth/me` with `PageSkeleton` while loading.

## Auth

- Zustand `tennis-explore-auth` (user, accessToken, refreshToken), `AuthProvider` calls `validateSession()` on mount, `axios` auto-retries 401 via `POST /auth/refresh` (7d) queue.
- Login `admin@tennisexplore.au / admin123` or `coach@tennisexplore.au / coach123`
- Header dropdown `Change Password` → `PUT /auth/me/password` (Formik/Yup, self only).

## Design System

- **Font:** `Inter` everywhere (`Playfair Display` removed, `index.css` `font-sans`, `TennisExploreHero` + `login` unified)
- **User account:** `header` `h-[84px]` (+30%), `h-12 w-12` initials `bg-primary`, pill `bg-primary/10 border-2 border-primary/30 shadow-md`, `w-72` dropdown — very visible, no image.
- **Colors:** `primary #c2e94e`, `te` surfaces `#0a0e14` etc., tokens in `tailwind.config.js`.

## Tech Stack

- **React 18** + **React Router 7** + **Vite 6** (lazy + manualChunks)
- **Zustand** + **TanStack Query** + **Axios** (refresh)
- **Formik** + **Yup** + **shadcn/ui** (Radix + CVA + Skeleton)
- **Tailwind CSS 3**, **Framer Motion**, **Material Symbols** (Inter)
