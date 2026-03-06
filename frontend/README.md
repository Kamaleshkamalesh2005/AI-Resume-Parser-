# Frontend - Resume Parser UI

React + TypeScript web application for uploading resumes and viewing matches.

## 🚀 Quick Start

### Prerequisites
- Node.js 16+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173` (Vite default)

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/                # Reusable React components
│   │   ├── UploadArea.tsx         # Resume upload component
│   │   ├── ResultsDisplay.tsx     # Results display component
│   │   ├── Nav.tsx                # Navigation bar
│   │   └── ...
│   │
│   ├── pages/                     # Full page components
│   │   ├── Dashboard.tsx          # Main dashboard
│   │   ├── Upload.tsx             # Upload page
│   │   ├── Results.tsx            # Results page
│   │   └── ...
│   │
│   ├── api/                       # API client functions
│   │   ├── client.ts              # HTTP client setup
│   │   ├── resume.ts              # Resume endpoints
│   │   └── match.ts               # Matching endpoints
│   │
│   ├── store/                     # State management (Zustand/Redux)
│   ├── types/                     # TypeScript type definitions
│   ├── utils/                     # Utility functions
│   ├── styles/                    # Global CSS
│   │
│   ├── App.tsx                    # Root component
│   ├── main.tsx                   # Entry point
│   └── vite-env.d.ts             # Vite type definitions
│
├── public/                        # Static assets
│   ├── images/
│   └── ...
│
├── index.html                     # HTML template
├── vite.config.ts                # Vite configuration
├── tsconfig.json                 # TypeScript configuration
├── tailwind.config.ts            # Tailwind CSS configuration
├── postcss.config.js             # PostCSS configuration
├── package.json                  # NPM dependencies
└── README.md                      # This file
```

## 🛠️ Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# API Configuration
VITE_API_URL=http://localhost:5000/api
VITE_API_TIMEOUT=30000

# Feature Flags
VITE_ENABLE_BATCH_UPLOAD=true
VITE_ENABLE_MATCHING=true
VITE_ENABLE_EXPORT=true

# UI Configuration
VITE_APP_NAME=Resume Parser
VITE_APP_VERSION=1.0.0
```

## 📦 Available Scripts

### Development
```bash
# Start development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npm run type-check
```

### Testing
```bash
# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

### Code Quality
```bash
# Lint code
npm run lint

# Format code
npm run format

# Type check
npm run type-check
```

## 🎨 Styling

The project uses **Tailwind CSS** for styling with custom configuration:

- **Colors**: Custom color palette defined in `tailwind.config.ts`
- **Components**: Custom component classes in CSS
- **Responsive**: Mobile-first responsive design

### Customizing Tailwind

Edit `tailwind.config.ts`:

```typescript
export default {
  theme: {
    extend: {
      colors: {
        primary: '#0066cc',
        // ... more colors
      },
    },
  },
}
```

## 🌐 API Integration

### Setup

The API client is configured in `src/api/client.ts`:

```typescript
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: import.meta.env.VITE_API_TIMEOUT,
})
```

### Example Usage

```typescript
// Upload resume
import { uploadResume } from '@/api/resume'

const response = await uploadResume(file)
console.log(response.data)  // Parsed resume data

// Get matches
import { getMatches } from '@/api/match'

const matches = await getMatches(resumeId, jobDescription)
console.log(matches)
```

## 🧪 Testing

### Setup Jest/Vitest

```bash
npm install --save-dev vitest jsdom @testing-library/react
```

### Write Tests

```typescript
import { render, screen } from '@testing-library/react'
import UploadArea from '@/components/UploadArea'

describe('UploadArea', () => {
  it('renders upload button', () => {
    render(<UploadArea />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })
})
```

### Run Tests

```bash
npm run test
npm run test:coverage
```

## 📱 Responsive Design

The application is fully responsive:

- **Mobile**: Single column layout, touch-optimized
- **Tablet**: Two column layout
- **Desktop**: Full multi-column layout

Use Tailwind responsive classes:

```typescript
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  {/* Content */}
</div>
```

## 🚀 Building for Production

### Build

```bash
npm run build
```

This creates an optimized build in the `dist/` directory:

- Minified JavaScript and CSS
- Image optimization
- Code splitting
- Hash-based file names for caching

### Preview

```bash
npm run preview
```

### Deploy

The `dist/` folder can be deployed to any static hosting:

- **Netlify**: Drag and drop `dist/`
- **Vercel**: Connect GitHub repo
- **AWS S3**: Use deployment script
- **Docker**: Use nginx container

### Docker Deployment

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🤝 Integration Points

### Connect to Backend

1. **API URL**: Update `VITE_API_URL` in `.env`
2. **Proxy**: Use Vite proxy in `vite.config.ts` for development:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '/api'),
    },
  },
}
```

3. **CORS**: Backend must have CORS enabled for `http://localhost:5173`

## 📚 Libraries

Key dependencies:

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **React Router** - Routing
- **Zustand/Redux** - State management (if used)

See `package.json` for complete list.

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Use different port
npm run dev -- --port 3000
```

### Build Issues

```bash
# Clean rebuild
rm -rf node_modules dist
npm install
npm run build
```

### API Connection Issues

1. Check backend is running: `http://localhost:5000`
2. Verify `VITE_API_URL` in `.env` matches backend
3. Check CORS headers in backend logs
4. Use browser DevTools Network tab to debug API calls

### TypeScript Errors

```bash
# Regenerate types
npm run type-check
```

## 📝 Component Development Guide

### Creating a New Component

```typescript
// src/components/MyComponent.tsx
import React from 'react'

interface MyComponentProps {
  title: string
  onSubmit: (data: string) => void
}

export const MyComponent: React.FC<MyComponentProps> = ({
  title,
  onSubmit,
}) => {
  return (
    <div className="p-4 bg-white rounded-lg shadow">
      <h2 className="text-xl font-bold">{title}</h2>
      {/* Component content */}
    </div>
  )
}
```

### Using in Page

```typescript
import { MyComponent } from '@/components/MyComponent'

export default function MyPage() {
  return (
    <MyComponent
      title="My Component"
      onSubmit={(data) => console.log(data)}
    />
  )
}
```

## 🔐 Security

Best practices for the frontend:

- **HTTPS Only**: Use HTTPS in production
- **Secure Storage**: Don't store sensitive data in localStorage
- **Input Validation**: Validate user input before submitting
- **XSS Prevention**: Use React's built-in HTML escaping
- **CSRF Protection**: Include CSRF token in requests (if needed)

## 🎯 Performance Optimization

- **Code Splitting**: Use React.lazy() for route-based splitting
- **Image Optimization**: Use WebP format with fallbacks
- **Bundle Analysis**: `npm run build -- --analyze`
- **Compression**: Enable gzip in server

```typescript
// Route-based code splitting
const Dashboard = React.lazy(() => import('@/pages/Dashboard'))

<Suspense fallback={<Loading />}>
  <Dashboard />
</Suspense>
```

---

**Status**: ✅ Ready for Development | **Framework**: React 18 + TypeScript | **Build Tool**: Vite | **Last Updated**: March 2026
