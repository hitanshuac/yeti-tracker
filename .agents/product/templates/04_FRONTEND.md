# Frontend Specification

## 1. Core Mandate
A high-fidelity, production-grade interface is explicitly **in scope** to showcase the project to judges and demonstrate the complete Medallion architecture loop.

## 2. Technology Stack
- **Framework**: Vite + React
- **Styling**: Vanilla CSS (No Tailwind, as per Advanced Agentic Coding rules).
- **Aesthetic**: Rich dark mode (#0D1117 background), glassmorphism components, vibrant neon accents (cyan/purple), micro-animations on hover.

## 3. Core Features
- **Activity Submission Form**: Real-time validation for adding transport/electricity usage.
- **Insights Dashboard**: Visual breakdown of carbon footprint trends over time.
- **Graceful Fallbacks**: Error boundaries to catch rendering failures. Offline-capable UI elements that alert the user if the backend connection is lost.

## 4. Accessibility (Hack2Skill Mandate)
- **Semantic HTML**: UI must rely heavily on semantic HTML5 elements.
- **ARIA Roles**: Custom interactive elements must feature appropriate ARIA states.
- **Keyboard Navigation**: Entire application must be navigable without a mouse.
- **High Contrast**: Text and actionable components must meet WCAG 2.1 AA contrast requirements against the dark navy background.

## 5. Build Constraints
- Must remain lightweight to respect the repository's 10MB limit.
- Dev server is run via `npm run dev`.
