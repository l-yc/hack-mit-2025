import { prisma } from './prisma';
import { Asset } from '@/types/asset';

// Asset operations using Prisma
export async function createAsset(asset: Omit<Asset, 'id' | 'created_at' | 'updated_at'>): Promise<Asset> {
  const result = await prisma.asset.create({
    data: {
      name: asset.name,
      url: asset.url,
      type: asset.type,
      size: asset.size,
      tags: asset.tags,
      metadata: asset.metadata,
    },
  });
  
  return {
    id: result.id,
    name: result.name,
    url: result.url,
    type: result.type,
    size: Number(result.size),
    tags: result.tags,
    metadata: result.metadata as Record<string, any>,
    created_at: result.createdAt.toISOString(),
    updated_at: result.updatedAt.toISOString(),
  };
}

export async function getAllAssets(): Promise<Asset[]> {
  const results = await prisma.asset.findMany({
    orderBy: { createdAt: 'desc' },
  });
  
  return results.map((result: any) => ({
    id: result.id,
    name: result.name,
    url: result.url,
    type: result.type,
    size: Number(result.size),
    tags: result.tags,
    metadata: result.metadata as Record<string, any>,
    created_at: result.createdAt.toISOString(),
    updated_at: result.updatedAt.toISOString(),
  }));
}

export async function updateAssetTags(id: number, tags: string[]): Promise<Asset> {
  const result = await prisma.asset.update({
    where: { id },
    data: { tags },
  });
  
  return {
    id: result.id,
    name: result.name,
    url: result.url,
    type: result.type,
    size: Number(result.size),
    tags: result.tags,
    metadata: result.metadata as Record<string, any>,
    created_at: result.createdAt.toISOString(),
    updated_at: result.updatedAt.toISOString(),
  };
}

export async function deleteAsset(id: number): Promise<void> {
  await prisma.asset.delete({
    where: { id },
  });
}

export async function searchAssets(query: string, tags?: string[]): Promise<Asset[]> {
  const whereConditions: Record<string, any> = {
    OR: [
      { name: { contains: query, mode: 'insensitive' } },
      { metadata: { path: ['location'], string_contains: query } },
      { metadata: { path: ['mood'], string_contains: query } },
      { tags: { has: query } },
    ],
  };

  if (tags && tags.length > 0) {
    whereConditions.AND = {
      tags: { hasEvery: tags },
    };
  }

  const results = await prisma.asset.findMany({
    where: query ? whereConditions : tags && tags.length > 0 ? { tags: { hasEvery: tags } } : {},
    orderBy: { createdAt: 'desc' },
  });
  
  return results.map((result: any) => ({
    id: result.id,
    name: result.name,
    url: result.url,
    type: result.type,
    size: Number(result.size),
    tags: result.tags,
    metadata: result.metadata as Record<string, any>,
    created_at: result.createdAt.toISOString(),
    updated_at: result.updatedAt.toISOString(),
  }));
}
