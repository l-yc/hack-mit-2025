import { NextRequest, NextResponse } from 'next/server';
import { writeFile } from 'fs/promises';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { createAsset, getAllAssets, searchAssets } from '@/lib/db-direct';
import sharp from 'sharp';
import { saveFile, getFileMetadata } from '@/lib/upload';
import { Asset } from '@/types/asset';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('q');
    const tags = searchParams.get('tags')?.split(',').filter(Boolean);

    let assets: Asset[];
    
    if (query || (tags && tags.length > 0)) {
      assets = await searchAssets(query || '', tags);
    } else {
      assets = await getAllAssets();
    }

    return NextResponse.json({ assets });
  } catch (error) {
    console.error('Error fetching assets:', error);
    return NextResponse.json({ error: 'Failed to fetch assets' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const files = formData.getAll('files') as File[];
    
    if (!files || files.length === 0) {
      return NextResponse.json({ error: 'No files provided' }, { status: 400 });
    }

    const uploadedAssets: Asset[] = [];

    for (const file of files) {
      if (file.size === 0) continue;

      // Save file to disk
      const buffer = Buffer.from(await file.arrayBuffer());
      const filename = `${uuidv4()}.jpg`; // Always save as JPG for compression
      const filepath = path.join(process.cwd(), 'public/uploads', filename);
      
      // Compress image using sharp
      let processedBuffer = buffer;
      if (file.type.startsWith('image/')) {
        processedBuffer = await sharp(buffer)
          .resize(1200, 1200, { fit: 'inside', withoutEnlargement: true })
          .jpeg({ quality: 80 })
          .toBuffer();
      }
      
      await writeFile(filepath, processedBuffer);

      // Basic metadata without auto-generated tags
      const basicMetadata = {
        width: 1080,
        height: 1080,
      };

      // Create asset in database
      const asset = await createAsset({
        name: file.name,
        url: `/uploads/${filename}`,
        type: file.type,
        size: processedBuffer.length,
        tags: [],
        metadata: basicMetadata,
      });

      uploadedAssets.push(asset);
    }

    return NextResponse.json({ assets: uploadedAssets });
  } catch (error) {
    console.error('Error uploading assets:', error);
    return NextResponse.json({ error: 'Failed to upload assets' }, { status: 500 });
  }
}
