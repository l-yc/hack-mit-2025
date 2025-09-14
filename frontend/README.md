# Hyperfeed - Social Media Content Generator

A full-stack web application for uploading, managing, and generating social media content using AI assistance.

## Features

### Assets Management
- **File Upload**: Upload images and videos with backend storage
- **Advanced Search**: Search by location, people, subjects, colors, mood, and tags
- **Tag Management**: Add and remove tags from assets
- **Metadata Display**: View asset metadata on hover
- **Database Storage**: PostgreSQL backend for persistent asset storage

### Content Generation
- **Content Type Selection**: Choose from Instagram Post, Story, or Reel formats
- **AI Chat Interface**: Guided conversation flow for content creation
- **Asset Selection**: AI automatically selects relevant assets based on user input
- **Interactive Carousel**: Navigate through selected images with arrows and indicators
- **Editable Captions**: Full text editor for post captions with character count
- **Export Options**: Download content or post directly to Instagram (API ready)

### State Management
- **Persistent State**: Tab state preserved when navigating between pages
- **Context Provider**: Centralized state management across components
- **Real-time Updates**: Live updates when assets are added or modified

## Tech Stack

- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, Heroicons
- **Backend**: Next.js API Routes, PostgreSQL, Node.js
- **Database**: PostgreSQL with JSONB support for metadata
- **File Storage**: Local file system with organized uploads directory
- **State Management**: React Context API

## Getting Started

### Prerequisites
- Node.js 18+ 
- PostgreSQL database
- npm or yarn

### Installation

1. Clone the repository
2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
Create a `.env.local` file with:
```
DATABASE_URL=postgresql://username:password@localhost:5432/contentgen
```

4. Set up the database:
```bash
node scripts/setup-db.js
```

5. Create uploads directory:
```bash
mkdir -p public/uploads
```

6. Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Project Structure

```
├── app/
│   ├── api/assets/          # Asset management API routes
│   ├── components/          # Reusable UI components
│   ├── generate/           # Content generation page
│   └── page.tsx            # Assets management page
├── lib/
│   ├── context.tsx         # Global state management
│   ├── db.ts              # Database operations
│   └── upload.ts          # File upload utilities
├── types/
│   └── asset.ts           # TypeScript type definitions
├── scripts/
│   └── setup-db.js        # Database setup script
└── public/uploads/        # File storage directory
```

## API Endpoints

- `GET /api/assets` - Fetch all assets or search with query parameters
- `POST /api/assets` - Upload new assets
- `PATCH /api/assets/[id]` - Update asset tags
- `DELETE /api/assets/[id]` - Delete an asset

## Database Schema

### Assets Table
- `id` (SERIAL PRIMARY KEY)
- `name` (VARCHAR) - Original filename
- `url` (TEXT) - File path/URL
- `type` (VARCHAR) - File type (image/video)
- `size` (BIGINT) - File size in bytes
- `tags` (TEXT[]) - Array of user-defined tags
- `metadata` (JSONB) - Flexible metadata storage
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

## Features in Detail

### Asset Upload Flow
1. User selects files via drag-drop or file picker
2. Files are uploaded to `/api/assets` endpoint
3. Server saves files to `public/uploads/` directory
4. Database record created with metadata
5. UI updates with new assets

### Content Generation Flow
1. User selects content type (Post/Story/Reel)
2. AI assistant prompts for purpose and target audience
3. User specifies project/theme for asset selection
4. AI automatically selects relevant assets
5. Generated caption displayed in editable text field
6. User can navigate carousel and edit content
7. Export or post to Instagram

### Search and Filtering
- Full-text search across asset names and metadata
- Tag-based filtering with visual tag selector
- Advanced search supports multiple metadata fields
- Real-time filtering as user types

## Development Notes

- Uses PostgreSQL JSONB for flexible metadata storage
- File uploads handled with FormData and stored locally
- State management via React Context prevents data loss on navigation
- Responsive design works on desktop and mobile
- TypeScript for type safety throughout the application

## Deployment

For production deployment:
1. Set up PostgreSQL database (Supabase, Railway, etc.)
2. Configure `DATABASE_URL` environment variable
3. Set up file storage (AWS S3, Cloudinary, etc.)
4. Deploy to Vercel, Netlify, or similar platform

## Future Enhancements

- Instagram API integration for direct posting
- User authentication and multi-user support
- Cloud file storage integration
- Advanced AI content generation
- Batch asset operations
- Asset organization with folders/projects
