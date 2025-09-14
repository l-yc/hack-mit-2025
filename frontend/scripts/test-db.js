const { Pool } = require('pg');
require('dotenv').config({ path: '.env.local' });

console.log(process.env.DATABASE_URL);

async function testConnection() {
  // Parse the connection string manually to avoid IPv6 issues
  const url = new URL(process.env.DATABASE_URL);
  
  const pool = new Pool({
    user: url.username,
    password: url.password,
    host: url.hostname,
    port: parseInt(url.port),
    database: url.pathname.slice(1),
    ssl: { rejectUnauthorized: false }
  });

  try {
    console.log('Testing database connection...');
    const client = await pool.connect();
    
    // Test basic connection
    const result = await client.query('SELECT NOW()');
    console.log('✅ Database connected successfully!');
    console.log('Current time from database:', result.rows[0].now);
    
    // Test if Asset table exists
    const tableCheck = await client.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'Asset'
      );
    `);
    
    if (tableCheck.rows[0].exists) {
      console.log('✅ Asset table exists');
      
      // Count existing assets
      const countResult = await client.query('SELECT COUNT(*) FROM "Asset"');
      console.log(`📊 Current assets in database: ${countResult.rows[0].count}`);
    } else {
      console.log('❌ Asset table does not exist - run the SQL script in Supabase first');
    }
    
    client.release();
    await pool.end();
    
  } catch (error) {
    console.error('❌ Database connection failed:', error.message);
    process.exit(1);
  }
}

testConnection();
