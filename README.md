# Social Media Content Generator

A full-stack application for generating AI-powered social media content with asset management and content creation capabilities.

## Architecture

### Frontend (`frontend/`)
- **Next.js 14** with TypeScript and Tailwind CSS
- **Pluggable Asset Service** - Switch between Flask and Prisma backends
- **React Context** for state management across tabs
- **Responsive UI** with drag-and-drop carousel and real-time search

### Backend (`backend/`)
- **Flask REST API** for image upload, storage, and AI-powered photo selection
- **AI Agents** for content rating and selection using Claude API
- **File Management** with validation, compression, and metadata extraction

## Quick Start

### 1. Backend Setup
```bash
cd backend/
pip install -r ../requirements.txt
export CLAUDE_API_KEY="your-claude-api-key"
python backend.py
```
Backend runs on `http://localhost:6741`

### 2. Frontend Setup
```bash
cd frontend/
npm install
cp env.example .env.local
# Edit .env.local with your configuration
npm run dev
```
Frontend runs on `http://localhost:3000`

## Configuration

### Asset Service Backend
The frontend can use either backend:

**Flask Backend (Default):**
```typescript
// frontend/lib/config.ts
export const config = {
  assetServiceType: 'flask' as 'flask' | 'prisma',
  flaskBackendUrl: 'http://localhost:6741'
};
```

**Prisma Backend:**
```typescript
export const config = {
  assetServiceType: 'prisma' as 'flask' | 'prisma'
};
```

### Environment Variables
```bash
# Flask Backend URL
NEXT_PUBLIC_FLASK_BACKEND_URL="http://localhost:6741"

# Claude API for AI features
CLAUDE_API_KEY="your-claude-api-key"

# Database (for Prisma backend)
DATABASE_URL="postgresql://user:pass@localhost:5432/db"
```

## API Endpoints

### Flask Backend (`backend/backend.py`)
- `POST /upload` - Upload single image
- `POST /upload/multiple` - Upload multiple images
- `GET /photos` - List all uploaded photos
- `GET /photos/<filename>` - Serve specific photo
- `DELETE /photos/<filename>` - Delete photo
- `POST /select` - AI-powered photo selection
- `GET /agents` - List available AI agents

### Frontend API (`frontend/app/api/`)
- `GET /api/assets` - Get assets with search/filtering
- `POST /api/assets` - Upload new assets
- `PUT /api/assets/[id]/tags` - Update asset tags

## Features

### Asset Management
- **Upload**: Drag-and-drop or click to upload images
- **Search**: Real-time search across names, metadata, and tags
- **Tagging**: Add/remove tags with keyboard shortcuts
- **Filtering**: Filter by multiple tags with AND logic
- **Deletion**: Remove unwanted assets

### Content Generation
- **AI Chat**: Interactive content generation with context
- **Asset Selection**: Choose images for content creation
- **Carousel**: Smooth sliding with drag/swipe support
- **Export**: Save generated content
- **Instagram Integration**: Direct posting capabilities

### AI-Powered Features
- **Photo Selection**: AI agents rate and select best photos
- **Content Generation**: Context-aware caption and content creation
- **Multiple Agents**: Different AI personalities for varied content styles

## Development

### Project Structure
```
├── backend/           # Flask API server
│   ├── backend.py     # Main Flask application
│   ├── prompter.py    # Claude API integration
│   ├── rater.py       # Photo rating logic
│   └── templater.py   # Template rendering
├── frontend/          # Next.js application
│   ├── app/           # App router pages
│   ├── lib/           # Utilities and services
│   │   ├── asset-service.ts  # Pluggable backend interface
│   │   ├── config.ts         # Configuration
│   │   └── context.tsx       # React context
│   └── types/         # TypeScript definitions
└── prompts/           # AI agent personalities
```

### Switching Backends
To switch from Flask to Prisma backend:

1. Update configuration:
```typescript
// frontend/lib/config.ts
export const config = {
  assetServiceType: 'prisma'
};
```

2. Set up database:
```bash
cd frontend/
npx prisma generate
npx prisma db push
```

3. Update environment variables in `.env.local`

## Deployment

### Frontend (Vercel)
```bash
cd frontend/
npm run build
vercel deploy
```

### Backend (Any Python hosting)
```bash
cd backend/
pip install -r ../requirements.txt
gunicorn backend:app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper TypeScript types
4. Test both Flask and Prisma backends
5. Submit a pull request

## License

MIT License - see LICENSE file for details
