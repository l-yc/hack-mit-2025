const { Pool } = require('pg');

// Simple database setup script
async function setupDatabase() {
  // For development, you can use a local PostgreSQL instance
  // or a service like Supabase, Neon, or Railway
  
  const connectionString = process.env.DATABASE_URL || 'postgresql://localhost:5432/contentgen';
  
  const pool = new Pool({
    connectionString,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
  });

  try {
    const client = await pool.connect();
    
    // Create assets table
    await client.query(`
      CREATE TABLE IF NOT EXISTS assets (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        type VARCHAR(50) NOT NULL,
        size BIGINT NOT NULL,
        tags TEXT[] DEFAULT '{}',
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
      );
    `);
    
    // Create indexes
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets USING GIN(tags);
    `);
    
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_assets_metadata ON assets USING GIN(metadata);
    `);
    
    console.log('✅ Database setup completed successfully');
    client.release();
    
  } catch (error) {
    console.error('❌ Database setup failed:', error);
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  setupDatabase();
}

module.exports = { setupDatabase };
