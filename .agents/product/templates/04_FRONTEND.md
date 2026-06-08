# 04_FRONTEND: Visual Validation Spec

## 1. UI Architecture
The UI is a "Single Pane of Glass" Data Science Dashboard. It is built strictly with `index.html` and Tailwind CSS, utilizing a premium Dark Glassmorphism aesthetic.

## 2. Component Design
### 2.1 Validation Panels (Top Row)
- **Diet Impact**: A horizontal bar chart component comparing Non-Veg, Mixed, and Veg `avg_co2`. Animated widths visually prove Diet as the primary driver.
- **Transport Impact**: A horizontal bar chart comparing Walk, EV, Bike, Bus, and Car.

### 2.2 Deep Dive Correlations (Bottom Row)
- **Electricity Impact Tiers**: Groups users into High/Medium/Low tiers and visualizes the massive disparity in carbon footprints.
- **Mythbusting Scorecards**: A 3-column grid displaying raw Pearson correlation coefficients.
  - Electricity (`0.42` - Strong Predictor)
  - Distance (`0.31` - Moderate)
  - Screen Time (`-0.03` - Zero Impact)

## 3. Styling Tokens
- **Background**: Deep obsidian (`#0d1322`).
- **Glass Panels**: `bg-white/5` with `backdrop-blur-xl` and `border-white/10`.
- **Primary Color**: Cyan/Teal (`#57f1db`) for strong positive highlights.
- **Typography**: `Inter` for clean, data-heavy readability. Monospace fonts used strictly for numerical outputs.

## 4. Interactivity
- Zero page reloads. Data is fetched asynchronously on DOM load via native `fetch()` calls.
- CSS transitions (`duration-1000`) provide smooth loading animations for the data bars, drawing the user's eye to the largest emitters.
