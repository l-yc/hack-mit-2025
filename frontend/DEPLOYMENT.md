# Deployment Guide for ContentGenAI

This guide covers deploying your social media content generator to Vercel with Prisma and PostgreSQL.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Database**: Set up a PostgreSQL database (recommended providers):
   - [Supabase](https://supabase.com) (Free tier available)
   - [Railway](https://railway.app) (Free tier available)
   - [Neon](https://neon.tech) (Free tier available)
   - [PlanetScale](https://planetscale.com) (MySQL alternative)

## Step 1: Database Setup

### Option A: Supabase (Recommended)
1. Create account at [supabase.com](https://supabase.com)
2. Create new project
3. Go to Settings → Database
4. Copy the connection string (URI format)
5. Replace `[YOUR-PASSWORD]` with your actual password

### Option B: Railway
1. Create account at [railway.app](https://railway.app)
2. Create new project → Add PostgreSQL
3. Go to PostgreSQL service → Connect tab
4. Copy the Database URL

### Option C: Neon
1. Create account at [neon.tech](https://neon.tech)
2. Create new project
3. Copy the connection string from dashboard

## Step 2: Deploy to Vercel

### Method 1: Vercel CLI (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy from project root
vercel

# Follow prompts:
# - Link to existing project? No
# - What's your project's name? social-media-content-generator
# - In which directory is your code located? ./
```

### Method 2: GitHub Integration
1. Push your code to GitHub
2. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
3. Click "New Project"
4. Import your GitHub repository
5. Configure build settings (should auto-detect Next.js)

## Step 3: Environment Variables

In Vercel dashboard:
1. Go to your project → Settings → Environment Variables
2. Add the following variables:

```
DATABASE_URL=your_postgresql_connection_string
PRISMA_GENERATE_DATAPROXY=true
NEXTAUTH_URL=https://your-app-name.vercel.app
NEXTAUTH_SECRET=your-random-secret-key
```

**Generate NEXTAUTH_SECRET:**
```bash
openssl rand -base64 32
```

## Step 4: Database Migration

After deployment, run database migration:

### Option A: Using Vercel CLI
```bash
# Set environment variable locally for migration
export DATABASE_URL="your_postgresql_connection_string"

# Push database schema
npx prisma db push
```

### Option B: Using Prisma Studio
```bash
# Open Prisma Studio to verify database
npx prisma studio
```

## Step 5: File Upload Configuration

For production file uploads, you have several options:

### Option A: Cloudinary (Recommended)
1. Sign up at [cloudinary.com](https://cloudinary.com)
2. Get your cloud name, API key, and API secret
3. Add environment variables:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### Option B: AWS S3
1. Create S3 bucket
2. Set up IAM user with S3 permissions
3. Add environment variables:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
AWS_S3_BUCKET=your_bucket_name
```

### Option C: Vercel Blob (Beta)
```bash
npm install @vercel/blob
```

## Step 6: Verify Deployment

1. Visit your deployed URL
2. Test asset upload functionality
3. Test content generation flow
4. Check database connections in Prisma Studio

## Troubleshooting

### Common Issues

**Build Errors:**
- Ensure all environment variables are set
- Check that `prisma generate` runs in build process
- Verify database connection string format

**Database Connection Issues:**
- Ensure DATABASE_URL is correctly formatted
- Check database provider allows external connections
- Verify SSL settings match your provider

**File Upload Issues:**
- Implement cloud storage for production
- Vercel has file system limitations
- Consider using Vercel Blob or external storage

### Build Commands

If auto-detection fails, set these manually in Vercel:

**Build Command:**
```bash
prisma generate && next build
```

**Install Command:**
```bash
npm install
```

**Development Command:**
```bash
next dev
```

## Performance Optimization

1. **Database Indexing**: Prisma schema includes optimized indexes
2. **Image Optimization**: Use Next.js Image component
3. **Caching**: Implement Redis for session storage
4. **CDN**: Vercel automatically provides CDN

## Security Considerations

1. **Environment Variables**: Never commit secrets to git
2. **Database Access**: Use connection pooling
3. **File Uploads**: Validate file types and sizes
4. **Rate Limiting**: Implement API rate limiting

## Monitoring

1. **Vercel Analytics**: Built-in performance monitoring
2. **Database Monitoring**: Use your provider's dashboard
3. **Error Tracking**: Consider Sentry integration
4. **Logs**: Check Vercel function logs

## Custom Domain (Optional)

1. Go to Vercel project → Settings → Domains
2. Add your custom domain
3. Configure DNS records as instructed
4. Update NEXTAUTH_URL environment variable

## Scaling Considerations

- **Database**: Upgrade plan as usage grows
- **File Storage**: Monitor storage usage
- **Vercel Functions**: Consider Pro plan for higher limits
- **CDN**: Optimize asset delivery

Your ContentGenAI app is now deployed and ready for production use!
