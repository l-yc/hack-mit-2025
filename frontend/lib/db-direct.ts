import { Pool } from 'pg';
import { Asset } from '@/types/asset';

// Create a connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});

export async function createAsset(assetData: Omit<Asset, 'id' | 'created_at' | 'updated_at'>): Promise<Asset> {
  const client = await pool.connect();
  try {
    const result = await client.query(
      `INSERT INTO "Asset" (name, url, type, size, tags, metadata) 
       VALUES ($1, $2, $3, $4, $5, $6) 
       RETURNING *`,
      [assetData.name, assetData.url, assetData.type, assetData.size, assetData.tags, assetData.metadata]
    );
    
    const row = result.rows[0];
    return {
      id: row.id,
      name: row.name,
      url: row.url,
      type: row.type,
      size: row.size,
      tags: row.tags,
      metadata: row.metadata,
      created_at: row.createdAt.toISOString(),
      updated_at: row.updatedAt.toISOString(),
    };
  } finally {
    client.release();
  }
}

export async function getAllAssets(): Promise<Asset[]> {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT * FROM "Asset" ORDER BY "createdAt" DESC');
    return result.rows.map(row => ({
      id: row.id,
      name: row.name,
      url: row.url,
      type: row.type,
      size: row.size,
      tags: row.tags,
      metadata: row.metadata,
      created_at: row.createdAt.toISOString(),
      updated_at: row.updatedAt.toISOString(),
    }));
  } finally {
    client.release();
  }
}

export async function updateAssetTags(id: number, tags: string[]): Promise<Asset> {
  const client = await pool.connect();
  try {
    const result = await client.query(
      'UPDATE "Asset" SET tags = $1, "updatedAt" = CURRENT_TIMESTAMP WHERE id = $2 RETURNING *',
      [tags, id]
    );
    
    const row = result.rows[0];
    return {
      id: row.id,
      name: row.name,
      url: row.url,
      type: row.type,
      size: row.size,
      tags: row.tags,
      metadata: row.metadata,
      created_at: row.createdAt.toISOString(),
      updated_at: row.updatedAt.toISOString(),
    };
  } finally {
    client.release();
  }
}

export async function deleteAsset(id: number): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query('DELETE FROM "Asset" WHERE id = $1', [id]);
  } finally {
    client.release();
  }
}

export async function searchAssets(query: string, tags?: string[]): Promise<Asset[]> {
  const client = await pool.connect();
  try {
    let sql = `
      SELECT * FROM "Asset" 
      WHERE (
        name ILIKE $1 OR 
        metadata->>'location' ILIKE $1 OR 
        metadata->>'mood' ILIKE $1 OR 
        $1 = ANY(tags)
      )
    `;
    const params: any[] = [`%${query}%`];
    
    if (tags && tags.length > 0) {
      sql += ' AND tags @> $2';
      params.push(tags);
    }
    
    sql += ' ORDER BY "createdAt" DESC';
    
    const result = await client.query(sql, params);
    return result.rows.map(row => ({
      id: row.id,
      name: row.name,
      url: row.url,
      type: row.type,
      size: row.size,
      tags: row.tags,
      metadata: row.metadata,
      created_at: row.createdAt.toISOString(),
      updated_at: row.updatedAt.toISOString(),
    }));
  } finally {
    client.release();
  }
}
