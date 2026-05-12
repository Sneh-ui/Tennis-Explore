# Tennis-Explore Dashboard

A professional React.js application for tennis analytics, built with **Vite**, **React Router**, **Tailwind CSS**, and **shadcn/ui** components.

## Project Structure

```
src/
├── components/
│   ├── layout/           # App shell: Sidebar, Header, AppLayout
│   │   ├── app-layout.jsx
│   │   ├── header.jsx
│   │   └── sidebar.jsx
│   ├── shared/           # Reusable domain components
│   │   ├── data-table.jsx
│   │   ├── icon.jsx
│   │   ├── insight-card.jsx
│   │   ├── media-card.jsx
│   │   ├── page-header.jsx
│   │   ├── progress-bar.jsx
│   │   ├── search-input.jsx
│   │   └── stat-card.jsx
│   └── ui/               # shadcn/ui primitives
│       ├── avatar.jsx
│       ├── button.jsx
│       ├── card.jsx
│       ├── input.jsx
│       ├── label.jsx
│       ├── scroll-area.jsx
│       ├── select.jsx
│       ├── separator.jsx
│       ├── tabs.jsx
│       ├── textarea.jsx
│       └── tooltip.jsx
├── data/
│   └── constants.js      # All mock data and configuration
├── lib/
│   └── utils.js          # cn() helper for Tailwind class merging
├── pages/
│   ├── dashboard.jsx     # Main analytics dashboard
│   ├── data-portal.jsx   # Match data explorer with filters + table
│   ├── media-library.jsx # Media file grid with type tabs
│   ├── ai-chatbot.jsx    # AI assistant chat interface
│   └── archive.jsx       # Placeholder page
├── App.jsx               # Router configuration
├── main.jsx              # Entry point
└── index.css             # Tailwind + global styles
```

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Design System

The app uses a custom "Modern Sports Analytics" design system:

- **Primary green**: `#0d631b` — Tennis green for actions & branding
- **Typography**: Inter font with a full scale from display to label
- **Surfaces**: Layered off-white tones (`#f7fbf0` → `#ffffff`) for depth
- **Border radius**: `0.75rem` for cards, `0.5rem` for inputs

All tokens are defined in `tailwind.config.js` and used consistently across every component.

## Tech Stack

- **React 18** + **React Router 7**
- **Vite 6** for build tooling
- **Tailwind CSS 3** with custom design tokens
- **shadcn/ui** (Radix primitives + CVA variants)
- **Lucide React** for supplementary icons
- **Material Symbols** for primary iconography
