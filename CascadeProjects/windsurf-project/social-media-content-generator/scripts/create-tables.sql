-- Create the assets table manually
CREATE TABLE IF NOT EXISTS "Asset" (
    "id" SERIAL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "size" INTEGER NOT NULL,
    "tags" TEXT[] DEFAULT '{}',
    "metadata" JSONB DEFAULT '{}',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "Asset_tags_idx" ON "Asset" USING GIN ("tags");
CREATE INDEX IF NOT EXISTS "Asset_metadata_idx" ON "Asset" USING GIN ("metadata");
CREATE INDEX IF NOT EXISTS "Asset_createdAt_idx" ON "Asset" ("createdAt");

-- Create a trigger to automatically update the updatedAt field
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW."updatedAt" = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_asset_updated_at 
    BEFORE UPDATE ON "Asset" 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
