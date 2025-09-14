import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { randomUUID } from 'crypto';

export async function saveFile(file: File): Promise<string> {
  const bytes = await file.arrayBuffer();
  const buffer = Buffer.from(bytes);

  // For Vercel, we'll use a temporary directory approach
  // In production, you should use a cloud storage service like AWS S3, Cloudinary, etc.
  const uploadsDir = process.env.NODE_ENV === 'production' 
    ? '/tmp/uploads' 
    : join(process.cwd(), 'public', 'uploads');
  
  await mkdir(uploadsDir, { recursive: true });

  // Generate unique filename
  const fileExtension = file.name.split('.').pop();
  const fileName = `${randomUUID()}.${fileExtension}`;
  const filePath = join(uploadsDir, fileName);

  // Save file
  await writeFile(filePath, buffer);

  // Return public URL - in production you'd return the cloud storage URL
  return process.env.NODE_ENV === 'production' 
    ? `/api/files/${fileName}` // This would need a file serving API route
    : `/uploads/${fileName}`;
}

export function getFileMetadata(file: File) {
  return {
    name: file.name,
    size: file.size,
    type: file.type,
  };
}
