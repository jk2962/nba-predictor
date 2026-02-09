# Vercel Deployment Guide

## Overview
This project is configured for full-stack deployment on Vercel with:
- **Frontend**: React + Vite (static site)
- **Backend**: FastAPI (serverless Python functions)

## Prerequisites
- Vercel account
- Vercel CLI: `npm i -g vercel`

## ⚠️ Database Configuration Required

### Problem
The app currently uses SQLite (`sqlite:///./data/nba.db`), which doesn't work in serverless environments because:
- Functions are ephemeral (no persistent file system)
- Each request may hit a different function instance
- Data written in one request won't be available in the next

### Solution: Use Vercel Postgres

#### 1. Create Vercel Postgres Database
```bash
# In your Vercel project dashboard
# Storage → Create Database → Postgres
# Copy the connection string
```

#### 2. Add Environment Variables
In Vercel project settings, add:

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
POSTGRES_URL=postgresql://user:pass@host:5432/dbname
POSTGRES_PRISMA_URL=postgresql://user:pass@host:5432/dbname?pgbouncer=true
POSTGRES_URL_NON_POOLING=postgresql://user:pass@host:5432/dbname
```

#### 3. Update Backend Config
The app will automatically use `DATABASE_URL` environment variable if set (in [backend/app/config.py](backend/app/config.py)):

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/nba.db"  # Falls back to SQLite
```

#### 4. Add psycopg2 to Requirements
Update [api/requirements.txt](api/requirements.txt):
```
psycopg2-binary==2.9.9
```

#### 5. Initialize Database
After deployment, you'll need to seed data. Options:
- Run migration script locally connected to Vercel Postgres
- Create a one-time serverless function to seed data
- Use Vercel's cron jobs to update data periodically

## Deployment Steps

### 1. Install Vercel CLI
```bash
npm i -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Deploy
```bash
# First deployment (will prompt for configuration)
vercel

# Production deployment
vercel --prod
```

### 4. Configure Environment Variables
In Vercel Dashboard → Project → Settings → Environment Variables:
- `DATABASE_URL` - Your Postgres connection string
- Any other secrets from `.env.example`

### 5. Redeploy After Adding Env Vars
```bash
vercel --prod
```

## Important Limitations

### 1. ML Model Size
- Vercel serverless functions have a **250MB limit**
- XGBoost models + dependencies may approach this limit
- Monitor deployment logs for size warnings

### 2. Cold Starts
- First request after inactivity may take **5-15 seconds**
- ML model loading happens on cold start
- Consider using Vercel's warming strategies or move to Railway/Render if unacceptable

### 3. Execution Timeout
- Hobby plan: 10 seconds
- Pro plan: 60 seconds
- Enterprise: 900 seconds
- Model training must happen outside serverless functions

### 4. Memory Limit
- Default: 1024 MB
- Pro: Up to 3008 MB
- XGBoost predictions should fit, but monitor usage

## Alternative: Hybrid Deployment

If serverless limitations are problematic:

### Frontend on Vercel + Backend Elsewhere
1. Keep frontend on Vercel (fast, free)
2. Deploy backend to:
   - **Railway** (easy, $5/mo, persistent storage)
   - **Render** (free tier available)
   - **Fly.io** (global edge, $0-5/mo)

3. Update [vercel.json](vercel.json):
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend.railway.app/api/:path*"
    }
  ]
}
```

## Testing Locally

### With Vercel Dev Server
```bash
# Installs dependencies and runs both frontend and serverless API
vercel dev
```

### Traditional Development
```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm run dev
```

## Monitoring

After deployment:
- **Functions**: Vercel Dashboard → Functions tab
- **Logs**: Real-time logs in dashboard
- **Performance**: Response times and cold starts
- **Errors**: Error tracking in Functions tab

## Troubleshooting

### "Module not found" errors
- Verify `PYTHONPATH` in vercel.json
- Check api/requirements.txt includes all dependencies

### Database connection errors
- Verify DATABASE_URL environment variable
- Check Postgres database is accessible
- Ensure psycopg2-binary is in requirements.txt

### Function size exceeded
- Check deployment logs for size
- Remove unused dependencies
- Consider reducing model size or using model quantization

### Timeout errors
- Optimize slow endpoints
- Consider upgrading Vercel plan
- Move to traditional hosting if needed

## Production Checklist

- [ ] Vercel Postgres database created
- [ ] Environment variables configured
- [ ] psycopg2-binary added to api/requirements.txt
- [ ] Database migrated and seeded
- [ ] ML models uploaded and accessible
- [ ] CORS headers configured correctly
- [ ] Error tracking enabled
- [ ] Custom domain configured (optional)

## Cost Estimate

**Free Tier:**
- 100GB bandwidth
- Serverless function executions: 100GB-hours
- Good for side projects and demos

**Pro Plan ($20/mo):**
- 1TB bandwidth
- 1000GB-hours compute
- Custom domains, analytics

**Postgres:**
- Hobby: $0.15/GB storage + $0.15/GB transfer
- Typically $5-20/mo for small apps
