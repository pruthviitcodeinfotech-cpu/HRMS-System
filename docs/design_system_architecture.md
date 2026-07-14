# HRMS Enterprise Admin Web Application: Design System Architecture

This document defines the design tokens, visual elements, component rules, and layout styles for the **Enterprise HR & Payroll Management System (HRMS) Admin Web Application**. It establishes a design system that supports responsive layouts, dark mode, and high-density data tables.

---

## 1. Design System Tokens

Tokens are the design variables that define the visual style of the application. They are implemented as HSL variables in CSS to support dark mode.

### 1. Light and Dark Theme Tokens

```css
/* Color token assignments in HSL format */
:root {
  /* Brand colors */
  --primary: 224 86% 46%;       /* Deep Slate Blue */
  --primary-foreground: 0 0% 100%;
  
  /* Neutral colors */
  --background: 210 20% 98%;    /* Off-white */
  --foreground: 224 71.4% 4.1%;  /* Deep charcoal text */
  --card: 0 0% 100%;            /* Clean white card */
  --card-foreground: 224 71.4% 4.1%;
  
  /* Borders and controls */
  --border: 220 13% 91%;        /* Soft gray border */
  --input: 220 13% 91%;
  --ring: 224 86% 46%;
}

.dark {
  /* Brand colors */
  --primary: 217.2 91.2% 59.8%;  /* Vibrant blue tint */
  --primary-foreground: 222.2 47.4% 11.2%;
  
  /* Neutral colors */
  --background: 222.2 84% 4.9%;   /* Very dark navy */
  --foreground: 210 40% 98%;      /* Soft white text */
  --card: 222.2 84% 6.5%;         /* Navy card */
  --card-foreground: 210 40% 98%;
  
  /* Borders and controls */
  --border: 217.2 32.6% 17.5%;    /* Slate gray border */
  --input: 217.2 32.6% 17.5%;
  --ring: 224.3 76.3% 48%;
}
```

### 2. Status Colors (Consistent Across Themes)

Status colors are used to indicate system status, task progress, and user feedback:

*   **Success (Emerald):** HSL `142.1 76.2% 36.3%` — Green status indicator. Used for active employees, approved leaves, and finalized payroll.
*   **Warning (Amber):** HSL `37.9 90.2% 49.8%` — Orange status indicator. Used for pending approvals, shifts conflicts, and draft items.
*   **Destructive / Error (Rose):** HSL `346.8 77.2% 49.8%` — Red status indicator. Used for terminated status, exit dates, rejected leaves, and system errors.
*   **Information (Sky):** HSL `198.6 88.7% 48.4%` — Cyan status indicator. Used for system notes, notifications, and info tips.

---

## 2. Typography & Scale

The design system uses two font families to balance readability with data layout:
*   **Primary Font:** `Inter` or `Outfit` (sans-serif) — Used for general UI, body copy, page headers, forms, and navigation links.
*   **Tabular Font:** `JetBrains Mono` or standard monospaced font — Used for tables, attendance log timings, currency fields, and IDs to align column alignments.

### Typography Scales

| Class | Font Size | Line Height | Ideal Usage |
| :--- | :--- | :--- | :--- |
| **text-xs** | `0.75rem` (12px) | `1rem` (16px) | Form labels, table headers, metadata badges. |
| **text-sm** | `0.875rem` (14px)| `1.25rem` (20px)| Standard body text, table row inputs, descriptions. |
| **text-base**| `1rem` (16px) | `1.5rem` (24px) | Input text fields, normal button text. |
| **text-lg** | `1.125rem` (18px)| `1.75rem` (28px)| Small header subtitles, dialog titles. |
| **text-xl** | `1.25rem` (20px) | `1.75rem` (28px)| Page sub-headers, widget summary cards. |
| **text-2xl**| `1.5rem` (24px) | `2rem` (32px) | Main section headings, modal header labels. |
| **text-3xl**| `1.875rem` (30px)| `2.25rem` (36px)| Page main title (H1), payroll summary totals. |

### Font Weights
*   **Regular (400):** Default body copy, descriptions, and list values.
*   **Medium (500):** Table headers, primary buttons, and inputs.
*   **Semibold (600):** Card titles, tab labels, and sectional headers.
*   **Bold (700):** Main page headings and key analytical metric metrics.

---

## 3. Spacing, Borders, & Shadows

### Spacing System (4px Grid Base)
The spacing system controls padding, margins, and layout gaps:
*   `0.25rem` (4px) — Small padding, badge gaps, element offsets.
*   `0.5rem` (8px) — Button padding, list item gaps, small card layouts.
*   `1rem` (16px) — Card padding, input row spacing, table padding.
*   `1.5rem` (24px) — Page margins, large modal padding.

### Border Radius System
*   `xs` — `2px` (used for small check selectors and list borders).
*   `sm` — `4px` (used for input containers and small buttons).
*   `md` — `6px` (used for standard buttons, cards, and select controls).
*   `lg` — `8px` (used for modals, dialog panels, and primary sections).
*   `full` — Round pills (used for profile pictures and badges).

### Shadows (Elevation Scale)
*   **sm:** `0 1px 2px 0 rgba(0, 0, 0, 0.05)` — Text fields and simple inputs.
*   **base:** `0 1px 3px 0 rgba(0, 0, 0, 0.1)` — Default cards and widgets.
*   **md:** `0 4px 6px -1px rgba(0, 0, 0, 0.1)` — Dropdown selectors and tooltips.
*   **lg:** `0 10px 15px -3px rgba(0, 0, 0, 0.1)` — Modals and slide-out drawers.

---

## 4. Component Visual Rules

Components must adhere to strict visual guidelines:

### 1. Buttons
*   **Primary:** Solid slate blue (`--primary`) background with white text. Focus state displays a `2px` focus ring.
*   **Secondary:** Muted slate background with charcoal text. Used for non-primary actions.
*   **Outline:** Transparent background with a `--border` outline. Focus state displays a soft background fill.
*   **Destructive:** Solid rose background with white text. Used for terminating records or deleting configurations.

### 2. Inputs
*   **Standard Border:** `1px solid var(--border)`.
*   **Focus State:** Border changes to `var(--primary)` with a subtle outer ring.
*   **Error State:** Border changes to red with a red focus ring. Validation errors are displayed in small red text below the input field.

### 3. Cards & Widgets
*   **Layout:** White background (`--card`), standard border radius (`md`), and a subtle shadow (`base`).
*   **Padding:** Default is `1.5rem` (24px) to ensure proper spacing around content.

### 4. Tables (AG Grid Community)
*   **Header Row:** Darker background with bold, muted text (`text-xs`).
*   **Data Rows:** Standard row height of `44px` for readability, with grid lines and hover effects.
*   **Tabular Data:** Numeric columns (such as salary details or timings) use the monospaced tabular font to maintain column alignment.

---

## 5. Overlay, State, & Feedback UI

### 1. Alerts & Banners
*   **Container:** Uses a light background with a dark border matching the alert status color (Success, Warning, Error, Info).
*   **Content:** Displayed with an icon on the left, followed by the message.

### 2. Toast Notifications (Sonner)
*   **Layout:** Clean card layout with a success/error status icon.
*   **Behavior:** Appears in the bottom-right corner of the screen. Standard toasts automatically dismiss after 4 seconds; critical errors remain visible until manually dismissed.

### 3. Loading Skeletons
*   **Animation:** Uses a pulsing opacity transition (`animate-pulse`) to show layout placeholder shimmers.
*   **Structure:** Skeleton cards and rows mimic the shape of the components they represent.

### 4. Empty States
*   **Layout:** Centered in the page or container. Features a muted gray icon, a clear title, a description of why the table is empty, and a primary action button (e.g. *"Hire Employee"*).

### 5. Overlays (Modals & Drawers)
*   **Backdrop:** Uses a semi-transparent dark overlay with a blur effect (`backdrop-blur-sm`).
*   **Drawers:** Slide in from the right edge of the screen, occupying the full height. Used for complex configurations (such as creating an employee or setting up shifts).
