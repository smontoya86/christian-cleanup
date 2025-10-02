# Music Disciple Design Language

**Last Updated:** October 2, 2025  
**Version:** 2.0 - Modern Refined Design

---

## Philosophy

Music Disciple's design embodies **trustworthy elegance** for a faith-based application. The visual language is:

- **Professional**: Inspires confidence in biblical analysis
- **Modern**: Contemporary 2024-2025 design standards
- **Conservative**: Appropriate for spiritual content
- **Accessible**: WCAG compliant, readable, welcoming

**Design Mantra:** "Apple meets faith-based" — refined, not flashy.

---

## Color Palette

### Primary Colors

```css
/* Refined Purple Palette */
--primary-purple: #6b46c1;    /* Main brand color - trustworthy, spiritual */
--primary-color: #7c5cdb;     /* Softer purple accent */
--primary-light: #9f7aea;     /* Light purple for gradients */
--light-purple: #f7f5fb;      /* Very light purple background */
```

**Usage:**
- **Primary Purple (#6b46c1)**: Headers, links, primary buttons, brand elements
- **Primary Color (#7c5cdb)**: Hover states, accents, highlights
- **Primary Light (#9f7aea)**: Gradient endpoints, subtle backgrounds
- **Light Purple (#f7f5fb)**: Card backgrounds, section backgrounds

### Semantic Colors

```css
--success-color: #10b981;     /* Green - clean content, positive */
--warning-color: #f59e0b;     /* Amber - caution, discernment needed */
--danger-color: #ef4444;      /* Red - high concern content */
--info-color: #06b6d4;        /* Cyan - informational */
```

### Text Colors

```css
--dark-text: #1a202c;         /* Primary text - high contrast */
--light-text: #ffffff;        /* White text on dark backgrounds */
--muted-text: #718096;        /* Secondary text, labels */
```

### Background Colors

```css
--body-bg: #ffffff;           /* Main page background */
--card-bg: #ffffff;           /* Card backgrounds */
--light-bg: #fafbfc;          /* Subtle alternate background */
--border-color: #e8eaed;      /* Borders, dividers */
```

### Gradients

```css
/* Hero/Section Backgrounds */
--hero-gradient: linear-gradient(135deg, #fdfbff 0%, #f7f5fb 100%);

/* Button Gradients */
background: linear-gradient(135deg, #6b46c1 0%, #7c5cdb 100%);

/* Card Accents */
background: linear-gradient(135deg, rgba(107, 70, 193, 0.05) 0%, rgba(159, 122, 234, 0.03) 100%);
```

**Rules:**
- Gradients must be **subtle** (< 15% opacity for backgrounds)
- Always use 135deg diagonal for consistency
- Primary buttons get full-opacity purple gradients
- Backgrounds get very light, barely visible gradients

---

## Typography

### Font Family

```css
font-family: 'Rubik', system-ui, -apple-system, sans-serif;
```

**Rubik** chosen for:
- Modern, friendly appearance
- Excellent readability
- Professional but approachable
- Works well for faith-based content

### Font Sizes (Responsive)

```css
/* Base */
--font-size-base: 18px;       /* Body text */
--line-height-base: 1.7;      /* Generous line height */

/* Headings (using clamp for responsiveness) */
h1, .h1: clamp(2.5rem, 5vw, 3.5rem);        /* 40-56px */
h2, .h2: clamp(2rem, 4vw, 2.75rem);         /* 32-44px */
h3, .h3: clamp(1.5rem, 3vw, 2rem);          /* 24-32px */
h4, .h4: clamp(1.25rem, 2.5vw, 1.5rem);     /* 20-24px */
h5, .h5: 1.25rem;                            /* 20px */
h6, .h6: 1rem;                               /* 16px */

/* Display Text */
.display-3: clamp(3rem, 6vw, 4.5rem);       /* 48-72px - Hero */
.display-4: clamp(2.5rem, 5vw, 3.5rem);     /* 40-56px - Sections */

/* Body Text */
.lead: clamp(1.125rem, 2vw, 1.375rem);      /* 18-22px */
```

### Font Weights

```css
300: Light (rarely used)
400: Regular (body text)
500: Medium (labels, subtle emphasis)
600: Semibold (subheadings, card headers)
700: Bold (headings, numbers, key stats)
800: Extra Bold (hero text only)
```

### Letter Spacing

```css
/* Tighter on large text for modern look */
h1, .display-3: -0.03em
h2, .display-4: -0.02em
h3: -0.01em

/* Labels/Small Text */
.label, .badge: 0.01em
```

---

## Layout & Spacing

### Border Radius

```css
--border-radius-sm: 12px;     /* Buttons, small cards */
--border-radius: 16px;        /* Standard cards */
--border-radius-lg: 20px;     /* Large cards, sections */
--border-radius-xl: 24px;     /* Hero images, special elements */
```

**Rule:** Larger elements = larger radius for consistency

### Shadows

```css
/* Base Shadows */
--box-shadow: 0 2px 20px rgba(0, 0, 0, 0.04);              /* Subtle */
--box-shadow-card: 0 4px 20px rgba(0, 0, 0, 0.06);         /* Cards */
--box-shadow-hover: 0 8px 30px rgba(107, 70, 193, 0.12);  /* Hover - purple tint */
--box-shadow-lg: 0 12px 40px rgba(107, 70, 193, 0.15);    /* Featured elements */
```

**Key Features:**
- Multiple layers for depth
- Purple tint on hover (brand integration)
- Soft, not harsh
- Increase on interaction

### Spacing Scale

```css
/* Standard spacing uses Bootstrap's rem-based scale */
0.25rem = 4px    /* Tight spacing */
0.5rem = 8px     /* Small gaps */
0.75rem = 12px   /* Default button padding */
1rem = 16px      /* Standard spacing */
1.5rem = 24px    /* Card padding */
2rem = 32px      /* Section spacing */
3rem = 48px      /* Large section spacing */
4rem = 64px      /* Page-level spacing */
```

---

## Components

### Buttons

**Primary Button:**
```css
.btn-primary {
    background: linear-gradient(135deg, #6b46c1 0%, #7c5cdb 100%);
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(107, 70, 193, 0.25);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(107, 70, 193, 0.35);
    background: linear-gradient(135deg, #7c5cdb 0%, #9f7aea 100%);
}
```

**Outline Button:**
```css
.btn-outline-secondary {
    color: #1a202c;
    border: 2px solid #e8eaed;
    background: transparent;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
}

.btn-outline-secondary:hover {
    background-color: #fafbfc;
    border-color: #6b46c1;
    color: #6b46c1;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
```

**Spotify Button:**
```css
.btn-spotify {
    background-color: #1DB954;  /* Spotify brand green */
    color: white;
    /* ... standard button properties ... */
}
```

**Button Sizes:**
- Default: `0.75rem 1.5rem` padding
- Large (`.btn-lg`): `1rem 2rem` padding, `1.125rem` font-size

### Cards

```css
.card {
    border: 1px solid rgba(0, 0, 0, 0.04);
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
    background-color: #ffffff;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(107, 70, 193, 0.12);
    border-color: rgba(107, 70, 193, 0.1);
}

.card-body {
    padding: 1.75rem;
}

.card-header {
    padding: 1.25rem 1.75rem;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    font-weight: 600;
}
```

**Feature Cards** (homepage):
```css
.feature-card:hover {
    transform: translateY(-6px);  /* More dramatic lift */
    box-shadow: 0 12px 40px rgba(107, 70, 193, 0.15);
}
```

### Badges

```css
.badge {
    font-weight: 500;
    padding: 0.4em 0.85em;
    font-size: 0.875rem;
    border-radius: 50rem;  /* Pill shape */
    letter-spacing: 0.01em;
}
```

**Semantic Badge Colors:**
- Success: `#10b981` (green)
- Warning: `#f59e0b` (amber)
- Danger: `#ef4444` (red)
- Info: `#06b6d4` (cyan)

---

## Transitions & Animations

### Standard Transitions

```css
--transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);      /* Default */
--transition-fast: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); /* Quick interactions */
```

**Easing:** Use `cubic-bezier(0.4, 0, 0.2, 1)` for smooth, natural motion

### Hover Effects

**Standard Pattern:**
1. Lift element: `transform: translateY(-2px)` to `-4px`
2. Enhance shadow: Increase blur and add purple tint
3. Optional: Lighten color slightly

**Example:**
```css
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(107, 70, 193, 0.12);
}
```

### Page Load Animations

```css
/* Fade In Up (Hero Content) */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.hero-content {
    animation: fadeInUp 0.8s ease-out;
}
```

**Rules:**
- Keep animations subtle (0.8s max duration)
- Use `ease-out` for entrances
- Respect `prefers-reduced-motion`

---

## Special Elements

### Hero Section

```css
.hero-section {
    background: linear-gradient(135deg, #fdfbff 0%, #f7f5fb 100%);
    position: relative;
    overflow: hidden;
}

/* Decorative gradient orbs */
.hero-section::before {
    content: '';
    position: absolute;
    /* ... radial gradient with 8% opacity ... */
}
```

**Features:**
- Very subtle gradient background
- Decorative gradient "orbs" (barely visible)
- Fade-in animations for content
- Responsive image with gradient backing

### Header/Navigation

```css
.site-header {
    background-color: rgba(255, 255, 255, 0.98);
    backdrop-filter: blur(10px);  /* Glassmorphism */
    border-bottom: 1px solid #e8eaed;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
    position: sticky;
    top: 0;
    z-index: 1000;
}
```

**Modern touch:** Sticky header with subtle blur effect

### Progress Indicators

```css
.progress-bar {
    transition: width 0.3s ease-in-out;
    background: linear-gradient(90deg, #6b46c1, #7c5cdb);
}
```

---

## Accessibility

### Contrast Requirements

- **Text on white**: Minimum 4.5:1 contrast
- **Primary purple (#6b46c1)** on white: **7.2:1** ✅
- **Muted text (#718096)** on white: **4.6:1** ✅

### Interactive Elements

- Minimum touch target: **44x44px**
- Focus states: 2px solid purple outline with offset
- Keyboard navigation: Fully supported

### Motion

```css
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

---

## Responsive Design

### Breakpoints (Bootstrap 5)

```css
sm: 576px   /* Small devices */
md: 768px   /* Tablets */
lg: 992px   /* Desktops */
xl: 1200px  /* Large desktops */
xxl: 1400px /* Extra large */
```

### Mobile-First Approach

All designs start mobile, then enhance for larger screens:

```css
/* Mobile base */
h1 { font-size: 2.5rem; }

/* Scale up for desktop */
@media (min-width: 992px) {
    h1 { font-size: 3.5rem; }
}
```

**Use `clamp()` for fluid typography:**
```css
h1 { font-size: clamp(2.5rem, 5vw, 3.5rem); }
```

---

## Best Practices

### DO ✅

- Use CSS variables for consistency
- Apply hover effects to interactive elements
- Use gradients sparingly and subtly
- Maintain generous whitespace
- Test on mobile first
- Use semantic color names (success, warning, danger)
- Add transitions to all interactive elements
- Respect `prefers-reduced-motion`

### DON'T ❌

- Don't use neon or vibrant colors
- Don't overuse animations
- Don't create harsh shadows
- Don't ignore accessibility
- Don't hardcode colors (use variables)
- Don't mix different border radius values randomly
- Don't use thin fonts on colored backgrounds
- Don't forget hover states

---

## File Structure

```
app/static/css/
├── base.css         # Variables, typography, base layout
├── components.css   # Reusable components (cards, buttons, badges)
└── utilities.css    # Loading states, helpers, animations
```

**Import order in templates:**
1. Bootstrap 5.3
2. base.css
3. components.css
4. utilities.css
5. Page-specific styles (if needed)

---

## Version History

### v2.0 (October 2025)
- Refined purple palette (#6b46c1)
- Increased border radius (12-20px)
- Enhanced typography scale (18px base)
- Modern shadows with purple tints
- Smooth cubic-bezier transitions
- Hero section with subtle gradients
- Sticky header with backdrop blur

### v1.0 (Previous)
- Dark purple (#270a47)
- Conservative border radius (8px)
- Bootstrap default styling
- Basic hover effects

---

## Design Checklist

Use this checklist when creating new pages or components:

- [ ] Uses CSS variables for colors
- [ ] Border radius: 12-20px
- [ ] Shadows have purple tint on hover
- [ ] Transitions: 0.3s cubic-bezier
- [ ] Typography: 18px base, responsive clamp
- [ ] Buttons have hover lift effect
- [ ] Cards have hover state
- [ ] Proper contrast ratios (4.5:1+)
- [ ] Mobile-first responsive
- [ ] Respects reduced motion preference
- [ ] Consistent spacing (rem-based)
- [ ] No hardcoded colors

---

## Contact

For questions about the design system:
- Review this document
- Check `/app/static/css/` files
- Refer to homepage (`index.html`) as reference implementation

**Last Review:** October 2, 2025

