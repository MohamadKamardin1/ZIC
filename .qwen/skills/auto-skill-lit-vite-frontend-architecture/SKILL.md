---
name: lit-vite-frontend-architecture
description: Build modern frontend dashboards using Lit web components, Vite, TypeScript, Tailwind CSS, and Material Design 3 with vintage color palettes
source: auto-skill
extracted_at: '2026-06-21T04:54:57.072Z'
---

# Lit + Vite Frontend Architecture for Dashboards

## When to Use
When building a complete frontend application that needs:
- Framework-agnostic web components (Lit)
- Fast build tooling (Vite)
- Type safety (TypeScript strict mode)
- Utility-first styling (Tailwind CSS)
- Material Design 3 with custom color palettes
- Complex dashboards with multiple widgets and charts

## Tech Stack
- **Vite** 5.x - Build tool and dev server
- **Lit** 3.x - Web components (framework-agnostic)
- **TypeScript** 5.x - Strict mode enabled
- **Tailwind CSS** 3.x - Utility-first styling
- **Material Design 3** - Design system with custom tokens
- **Path aliases** - `@/`, `@components/`, `@features/`, `@core/`, etc.

## Project Structure
```
project/
├── .env.development
├── .env.staging
├── .env.production
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── index.html
├── package.json
├── public/
│   └── assets/
│       ├── images/
│       └── icons/
└── src/
    ├── main.ts
    ├── app.ts
    ├── config/
    │   ├── api.config.ts
    │   ├── auth.config.ts
    │   └── theme.config.ts
    ├── core/
    │   ├── api/
    │   ├── services/
    │   ├── store/
    │   ├── router/
    │   └── utils/
    ├── components/
    │   ├── common/
    │   └── layout/
    ├── features/
    │   ├── auth/
    │   ├── dashboard/
    │   └── [feature-modules]/
    ├── styles/
    ├── types/
    └── constants/
```

## Key Patterns

### Component Structure
```typescript
import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';

@customElement('component-name')
export class ComponentName extends LitElement {
  @state() private data: DataType | null = null;
  
  static styles = css`
    /* All styles scoped to component */
  `;
  
  render() {
    return html`...`;
  }
}
```

### State Management
- Use `@state()` for component-local reactive state
- Create singleton services for shared state (authService, dashboardService)
- Use stores for global application state (authStore, appStore)

### Dashboard Widgets
- Each widget is a separate Lit component
- Use SVG for charts (circular progress, line charts, gauges)
- Create mock data service with TypeScript interfaces matching backend API
- Animate on mount with CSS animations

### Material Design 3
- Define CSS custom properties for theme tokens
- Use vintage color palette: Indigo (#4F46E5), Purple (#7C3AED), Magenta (#DB2777)
- Apply shadows: `0 1px 3px rgba(0,0,0,0.05), 0 4px 12px rgba(0,0,0,0.05)`
- Border radius: 16px for cards

### Path Aliases
Configure in `tsconfig.json` and `vite.config.ts`:
```json
{
  "paths": {
    "@/*": ["src/*"],
    "@components/*": ["src/components/*"],
    "@features/*": ["src/features/*"],
    "@core/*": ["src/core/*"]
  }
}
```

## Graceful API Error Handling

### Mock data fallback pattern
When API calls fail, gracefully fall back to mock data to keep the UI functional:

```typescript
async connectedCallback() {
  super.connectedCallback();
  try {
    this.data = await dashboardDataService.getDashboardData();
  } catch (error) {
    console.warn('Failed to fetch dashboard data, using mock data:', error);
    this.data = this.getMockData(); // fallback
  }
  this.isLoading = false;
}

private getMockData(): DashboardData {
  // Return complete mock data matching API structure
  return {
    date: { day: '21', weekday: 'Sunday', month: 'June' },
    kpis: { monthlyGrowth: 15.7, activeUsers: 1, revenue: '$328.5M' },
    // ... complete mock data
  };
}
```

**Benefits**:
- UI remains functional even when backend is unavailable
- Easier development without requiring backend to be running
- Better user experience during network issues
- Console warnings help with debugging

## Debugging API Endpoint Issues

### Systematic approach to 404 errors
When frontend API calls return 404:

1. **Check the actual URL being called**:
   ```bash
   # Test endpoint directly
   curl -v -X GET http://localhost:8000/api/v1/users/me/ \
     -H "Authorization: Bearer $TOKEN" 2>&1 | tail -20
   ```

2. **Check backend URL registration**:
   ```bash
   cd backend && python manage.py show_urls | grep "users/me"
   # Output: /api/v1/users/users/me/ (note the double /users/)
   ```

3. **Understand DRF router patterns**:
   - `DefaultRouter` with `router.register(r'users', UserViewSet)` creates `/users/` base
   - `@action(detail=False, methods=['get']) def me()` creates `/users/me/`
   - Combined: `/api/v1/users/users/me/` (not `/api/v1/users/me/`)

4. **Fix API configuration**:
   ```typescript
   // If service baseUrl is /api/v1/users
   services: {
     users: { baseUrl: `${getBaseUrl()}/api/v1/users` }
   }
   // Then endpoint should be /users/me/ (relative to service)
   endpoints: {
     users: { profile: '/users/me/' }
   }
   // Full URL: /api/v1/users/users/me/ ✅
   ```

5. **Create separate API service files**:
   - `auth.api.ts` for authentication endpoints
   - `users.api.ts` for user management endpoints
   - Each extends `BaseAPI` with correct service name

### Service layer organization
When endpoints belong to different services:

```typescript
// ❌ WRONG - getCurrentUser in auth.api.ts calling users endpoint
class AuthAPI extends BaseAPI {
  constructor() { super('auth'); } // baseUrl: /api/v1/auth
  async getCurrentUser() {
    return this.get(API_CONFIG.endpoints.users.profile); // /users/me/
  }
}
// Result: /api/v1/auth/users/me/ ❌

// ✅ CORRECT - separate users.api.ts
class UsersAPI extends BaseAPI {
  constructor() { super('users'); } // baseUrl: /api/v1/users
  async getCurrentUser() {
    return this.get(API_CONFIG.endpoints.users.profile); // /users/me/
  }
}
// Result: /api/v1/users/users/me/ ✅
```

## Common Pitfalls
- **Vite Lit plugin**: `@vitejs/plugin-lit` doesn't exist — Vite handles Lit natively without a plugin. Remove it from `package.json` devDependencies and remove the `import lit from '@vitejs/plugin-lit'` from `vite.config.ts`. Use `plugins: []` instead.
- **Mock data alignment**: TypeScript interfaces must exactly match backend API response structure
- **Token management**: Store JWT tokens in localStorage, implement refresh logic
- **Route guards**: Check authentication status before rendering protected routes
- **SVG animations**: Use `stroke-dasharray` and `stroke-dashoffset` for circular progress animations
- **DRF router URL patterns**: Django REST Framework's `DefaultRouter` creates URLs like `/users/users/me/` when you register a ViewSet with `router.register(r'users', UserViewSet)` and add an `@action(detail=False) def me()`. The first `users` comes from the router registration, the second from the action name.
- **Service-based endpoint organization**: When using service-based API config, endpoints must be in the correct service file (e.g., `getCurrentUser()` belongs in `users.api.ts`, not `auth.api.ts`)
- **Graceful degradation**: Always implement mock data fallback for API failures — keeps UI functional during development and network issues

## API Configuration Pattern

### Service-based API config (avoid URL duplication)
When using a service-based API config where `baseUrl` already includes the service path, endpoint paths must NOT include the service path prefix:

```typescript
// ❌ WRONG — causes /api/v1/auth/auth/login
services: {
  auth: { baseUrl: `${getBaseUrl()}/api/v1/auth` }
}
endpoints: {
  auth: { login: '/auth/login' }  // duplicates /auth
}

// ✅ CORRECT — produces /api/v1/auth/login
services: {
  auth: { baseUrl: `${getBaseUrl()}/api/v1/auth` }
}
endpoints: {
  auth: { login: '/login' }  // no prefix — baseUrl already has it
}
```

### Dashboard API integration
- Replace mock data service with real API calls: `await dashboardAPI.getOverview()`
- Add caching with fallback: if API fails, return cached data
- Ensure `dashboardAPI` extends `BaseAPI` with proper service name

## SVG Icons in Lit Components

### unsafeHTML helper pattern
Lit doesn't natively support injecting raw SVG strings. Use a template-based helper:

```typescript
private unsafeHTML(svgContent: string) {
  const template = document.createElement('template');
  template.innerHTML = svgContent;
  return template.content;
}

private getIcon(iconName: string) {
  const icons: Record<string, string> = {
    home: `<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>...`,
    // ... more icons
  };
  return html`
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round">
      ${this.unsafeHTML(icons[iconName])}
    </svg>
  `;
}
```

## Animation Lifecycle in Lit

### Trigger animations after first render
Use `firstUpdated()` lifecycle method with `setTimeout` to ensure DOM is ready:

```typescript
protected firstUpdated() {
  setTimeout(() => {
    this.animateCountUp();
    this.animateCircularProgress();
    this.animateGauge();
    this.animateProgressBars();
    this.animateLineChart();
  }, 100);
}
```

### Count-up animation with requestAnimationFrame
```typescript
private animateCountUp() {
  const animateValue = (element: HTMLElement, target: number, duration = 1500) => {
    const startTime = performance.now();
    const update = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const current = Math.floor(eased * target);
      element.textContent = current.toString();
      if (progress < 1) requestAnimationFrame(update);
      else element.textContent = target.toString();
    };
    requestAnimationFrame(update);
  };
}
```

### Circular progress with staggered delays
```typescript
private animateCircularProgress() {
  const claims = [
    { id: 'claim-gc', percent: 14, delay: 300 },
    { id: 'claim-gl', percent: 26, delay: 500 },
    // ...
  ];
  claims.forEach(({ id, percent, delay }) => {
    setTimeout(() => {
      const el = this.shadowRoot?.querySelector(`#${id}`) as SVGCircleElement;
      if (el) {
        const circumference = 2 * Math.PI * 40;
        el.style.strokeDashoffset = (circumference - (percent / 100) * circumference).toString();
      }
    }, delay);
  });
}
```

### Line chart drawing animation
```typescript
private animateLineChart() {
  setTimeout(() => {
    const lines = ['line-ol', 'line-gl', 'line-gc'];
    lines.forEach((id, index) => {
      const line = this.shadowRoot?.querySelector(`#${id}`) as SVGPathElement;
      if (line) {
        const length = line.getTotalLength();
        line.style.strokeDasharray = length.toString();
        line.style.strokeDashoffset = length.toString();
        setTimeout(() => {
          line.style.transition = 'stroke-dashoffset 1.5s ease-out';
          line.style.strokeDashoffset = '0';
        }, index * 200);
      }
    });
  }, 600);
}
```

## Setup Steps
1. Initialize with `npm create vite@latest` (select TypeScript template)
2. Install Lit: `npm install lit`
3. Install Tailwind: `npm install -D tailwindcss postcss autoprefixer`
4. Configure path aliases in tsconfig and vite config
5. Create Material Design 3 theme tokens in CSS
6. Build component library (sidebar, header, footer, widgets)
7. Implement routing with guards
8. Create mock data service matching backend API
9. Connect to real backend API (add authentication headers)
