# Frontend Style Guide - Christian Music Curator

## Overview

This document outlines the coding standards, naming conventions, and best practices for frontend development in the Christian Music Curator project. Following these guidelines ensures consistency, maintainability, and performance across the application.

## Table of Contents

1. [CSS Guidelines](#css-guidelines)
2. [JavaScript Guidelines](#javascript-guidelines)
3. [HTML Template Guidelines](#html-template-guidelines)
4. [File Organization](#file-organization)
5. [Performance Best Practices](#performance-best-practices)
6. [Accessibility Standards](#accessibility-standards)
7. [Development Checklist](#development-checklist)

## CSS Guidelines

### Architecture

Our CSS follows a modular architecture with three main layers:

```
app/static/css/
├── base.css        # Core variables, typography, layout, dark mode
├── components.css  # Reusable UI components
└── utilities.css   # Helper classes, animations, skeleton loaders
```

### Naming Conventions

- **Use kebab-case** for class names: `.concern-badge`, `.playlist-card`
- **Use BEM methodology** for complex components:
  ```css
  /* Block */
  .analysis-progress {}
  
  /* Element */
  .analysis-progress__bar {}
  .analysis-progress__text {}
  
  /* Modifier */
  .analysis-progress--complete {}
  .analysis-progress__bar--danger {}
  ```

### CSS Variables

Use CSS custom properties for consistent theming:

```css
:root {
  --primary-color: #6f42c1;
  --success-color: #198754;
  --warning-color: #ffc107;
  --danger-color: #dc3545;
  --font-family-base: 'Roboto', Arial, sans-serif;
}
```

### Code Style

```css
/* ✅ Good */
.component {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: var(--background-color);
}

/* ❌ Avoid */
.component{display:flex;flex-direction:column;gap:1rem;padding:1rem;border-radius:.5rem;background-color:#ffffff;}
```

## JavaScript Guidelines

### Module Structure

Use ES6 modules with clear separation of concerns:

```javascript
// ✅ Good: Modular approach
import { UIHelpers } from '../utils/ui-helpers.js';
import { ApiService } from '../services/api-service.js';

export class PlaylistAnalysis {
  constructor() {
    this.uiHelpers = new UIHelpers();
    this.apiService = new ApiService();
  }
}

// ❌ Avoid: Monolithic approach
// One large file with all functionality mixed together
```

### Naming Conventions

- **Classes**: PascalCase → `PlaylistAnalysis`, `UIHelpers`
- **Functions/Methods**: camelCase → `analyzePlaylist()`, `showProgress()`
- **Constants**: SCREAMING_SNAKE_CASE → `API_ENDPOINTS`, `DEFAULT_TIMEOUT`
- **Variables**: camelCase → `playlistId`, `analysisResult`

### Function Documentation

```javascript
/**
 * Analyze a playlist and update the UI with progress
 * @param {string} playlistId - The Spotify playlist ID
 * @param {Object} options - Configuration options
 * @param {boolean} options.showProgress - Whether to show progress indicator
 * @returns {Promise<Object>} Analysis results
 */
async analyzePlaylist(playlistId, options = {}) {
  // Implementation
}
```

### Error Handling

Always use proper error handling with user-friendly messages:

```javascript
// ✅ Good
try {
  const result = await this.apiService.analyzePlaylist(playlistId);
  this.uiHelpers.showSuccess('Analysis completed successfully!');
  return result;
} catch (error) {
  this.uiHelpers.showError('Failed to analyze playlist. Please try again.');
  throw error;
}

// ❌ Avoid
// No error handling or console.log debugging
const result = await this.apiService.analyzePlaylist(playlistId);
console.log(result);
```

## HTML Template Guidelines

### Component-Based Architecture

Break down large templates into reusable components:

```html
<!-- ✅ Good: Using components -->
{% include "components/ui/page_header.html" %}
{% include "components/analysis/progress_indicator.html" %}
{% include "components/playlist/song_card.html" %}

<!-- ❌ Avoid: Monolithic templates -->
<!-- 800+ lines of HTML in one file -->
```

### Semantic HTML

Use appropriate semantic elements:

```html
<!-- ✅ Good -->
<article class="playlist-card">
  <header class="playlist-card__header">
    <h2 class="playlist-card__title">{{ playlist.name }}</h2>
  </header>
  <main class="playlist-card__content">
    <p class="playlist-card__description">{{ playlist.description }}</p>
  </main>
</article>

<!-- ❌ Avoid -->
<div class="playlist-card">
  <div class="playlist-card__header">
    <div class="playlist-card__title">{{ playlist.name }}</div>
  </div>
</div>
```

### Accessibility Attributes

Always include proper ARIA attributes and alt text:

```html
<!-- ✅ Good -->
<button 
  class="btn btn-primary" 
  aria-label="Analyze playlist {{ playlist.name }}"
  data-playlist-id="{{ playlist.id }}">
  <i class="fas fa-chart-line" aria-hidden="true"></i>
  Analyze
</button>

<img 
  src="{{ playlist.image_url }}" 
  alt="Cover art for {{ playlist.name }} playlist"
  loading="lazy">
```

## File Organization

### Directory Structure

```
app/static/
├── css/
│   ├── base.css              # Core styles
│   ├── components.css        # UI components
│   └── utilities.css         # Helper classes
├── js/
│   ├── main.js              # Entry point
│   ├── modules/             # Feature modules
│   │   └── playlist-analysis.js
│   ├── services/            # API and data services
│   │   └── api-service.js
│   ├── utils/               # Utility functions
│   │   └── ui-helpers.js
│   └── components/          # Standalone components
│       └── lazyLoader.js
├── images/                  # Static images
└── dist/                    # Built assets (auto-generated)
    ├── css/
    ├── js/
    └── images/
```

### Template Organization

```
app/templates/
├── base.html               # Base template
├── layouts/                # Layout templates
├── components/             # Reusable components
│   ├── analysis/          # Analysis-specific components
│   ├── playlist/          # Playlist-specific components
│   └── ui/                # Generic UI components
└── pages/                 # Page templates
```

## Performance Best Practices

### CSS Performance

1. **Load critical CSS in `<head>`**: Base layout and above-the-fold styles
2. **Async load non-critical CSS**: Icons, animations, below-the-fold styles
3. **Use CSS custom properties**: For consistent theming and easier maintenance
4. **Avoid deep nesting**: Keep specificity low (max 3 levels)

### JavaScript Performance

1. **Use `defer` attribute**: For non-critical scripts
2. **Implement code splitting**: Separate features into modules
3. **Lazy load components**: Load heavy components only when needed
4. **Use event delegation**: For dynamic content

### Image Optimization

1. **Use `loading="lazy"`**: For below-the-fold images
2. **Provide appropriate `alt` text**: For accessibility
3. **Use proper image formats**: WebP where supported, with fallbacks

### Build Process

Our build process includes:

- **CSS minification**: Using PostCSS with cssnano
- **JavaScript bundling**: Using ESBuild with tree shaking
- **Image optimization**: Using imagemin
- **Source maps**: For development debugging

## Accessibility Standards

### WCAG 2.1 AA Compliance

1. **Color contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
2. **Keyboard navigation**: All interactive elements must be keyboard accessible
3. **Screen reader support**: Proper ARIA labels and landmarks
4. **Focus management**: Visible focus indicators

### Implementation Examples

```html
<!-- Skip to main content -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- Proper form labels -->
<label for="playlist-search">Search playlists</label>
<input type="search" id="playlist-search" name="search">

<!-- Loading states -->
<button aria-live="polite" aria-describedby="loading-text">
  Analyze Playlist
  <span id="loading-text" class="sr-only">Loading...</span>
</button>
```

## Development Checklist

### Before Committing

- [ ] **CSS**: Follows naming conventions and architecture
- [ ] **JavaScript**: Uses proper error handling and documentation
- [ ] **HTML**: Uses semantic elements and accessibility attributes
- [ ] **Performance**: Critical resources are optimized
- [ ] **Testing**: All smoke tests pass
- [ ] **Build**: Production build works without errors
- [ ] **Linting**: No ESLint or Stylelint errors

### Performance Checklist

- [ ] CSS is modular and follows the three-file architecture
- [ ] Critical CSS loads in `<head>`, non-critical loads asynchronously
- [ ] JavaScript uses `defer` attribute and proper module loading
- [ ] Images have `loading="lazy"` and proper `alt` attributes
- [ ] External resources use `dns-prefetch` hints
- [ ] Build process generates optimized assets

### Accessibility Checklist

- [ ] All interactive elements are keyboard accessible
- [ ] Images have descriptive `alt` attributes
- [ ] Form inputs have proper labels
- [ ] Color contrast meets WCAG AA standards
- [ ] Screen reader support is tested
- [ ] Focus indicators are visible

### Browser Testing

Test in:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

## Tools and Resources

### Development Tools

- **Linting**: ESLint (JavaScript) + Stylelint (CSS)
- **Building**: ESBuild (JavaScript) + PostCSS (CSS)
- **Testing**: Jest (unit tests) + Pytest (integration)

### Performance Tools

- **Lighthouse**: For performance audits
- **WebPageTest**: For detailed performance analysis
- **Chrome DevTools**: For debugging and profiling

### Accessibility Tools

- **WAVE**: Web accessibility evaluation
- **axe DevTools**: Accessibility testing
- **Screen reader**: NVDA (Windows) or VoiceOver (Mac)

## Conclusion

Following these guidelines ensures:

1. **Consistency**: Uniform code style across the project
2. **Maintainability**: Easy to update and extend
3. **Performance**: Fast loading and responsive user experience
4. **Accessibility**: Inclusive design for all users
5. **Quality**: Reliable, tested, and production-ready code

For questions or suggestions about these guidelines, please refer to the project documentation or create an issue in the repository. 