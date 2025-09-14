// Asset service interface - pluggable backend abstraction
export interface AssetMetadata {
  width?: number;
  height?: number;
  location?: string;
  people?: string[];
  subjects?: string[];
  colors?: string[];
  mood?: string;
  [key: string]: any;
}

export interface Asset {
  id: string;
  name: string;
  url: string;
  type: string;
  size: number;
  tags: string[];
  metadata: AssetMetadata;
  created_at: string;
  updated_at?: string;
}

export interface AssetUploadResult {
  assets: Asset[];
  errors?: string[];
}

export interface AssetSearchOptions {
  query?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

// Abstract asset service interface
export abstract class AssetService {
  abstract uploadAssets(files: File[]): Promise<AssetUploadResult>;
  abstract getAssets(options?: AssetSearchOptions): Promise<Asset[]>;
  abstract updateAssetTags(id: string, tags: string[]): Promise<Asset>;
  abstract deleteAsset(id: string): Promise<void>;
}

// Flask backend implementation
export class FlaskAssetService extends AssetService {
  private baseUrl: string;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_FLASK_BACKEND_URL || 'http://localhost:6741') {
    super();
    this.baseUrl = baseUrl;
  }

  // Helper function to compress images
  private async compressImage(file: File, maxWidth: number = 1200, quality: number = 0.8): Promise<File> {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      
      img.onload = () => {
        // Calculate new dimensions
        let { width, height } = img;
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
        
        canvas.width = width;
        canvas.height = height;
        
        // Draw and compress
        ctx?.drawImage(img, 0, 0, width, height);
        canvas.toBlob(
          (blob) => {
            if (blob) {
              const compressedFile = new File([blob], file.name, {
                type: 'image/jpeg',
                lastModified: Date.now(),
              });
              resolve(compressedFile);
            } else {
              resolve(file); // Fallback to original
            }
          },
          'image/jpeg',
          quality
        );
      };
      
      img.onerror = () => resolve(file); // Fallback to original
      img.src = URL.createObjectURL(file);
    });
  }

  async uploadAssets(files: File[]): Promise<AssetUploadResult> {
    const imageFiles = files.filter(f => f.type.startsWith('image/'));
    const videoFiles = files.filter(f => f.type.startsWith('video/'));
    const uploadedAssets: Asset[] = [];
    const errors: string[] = [];

    // Handle images
    if (imageFiles.length === 1) {
      const formData = new FormData();
      const compressed = await this.compressImage(imageFiles[0]);
      formData.append('photo', compressed);
      const res = await fetch(`${this.baseUrl}/upload`, { method: 'POST', body: formData });
      if (res.ok) {
        const result = await res.json();
        uploadedAssets.push({
          id: result.filename,
          name: imageFiles[0].name,
          url: `${this.baseUrl}${result.file_url}`,
          type: imageFiles[0].type || 'image/jpeg',
          size: result.size_bytes,
          tags: [],
          metadata: {},
          created_at: result.upload_time,
        });
      } else {
        try { const j = await res.json(); errors.push(j.error || 'Image upload failed'); } catch { errors.push('Image upload failed'); }
      }
    } else if (imageFiles.length > 1) {
      const formData = new FormData();
      const compressedFiles = await Promise.all(
        imageFiles.map(file => this.compressImage(file))
      );
      compressedFiles.forEach(file => formData.append('photos', file));
      const res = await fetch(`${this.baseUrl}/upload/multiple`, { method: 'POST', body: formData });
      if (res.ok) {
        const result = await res.json();
        const assets: Asset[] = result.uploaded_files.map((file: any, index: number) => ({
          id: file.filename,
          name: imageFiles[index]?.name || file.original_filename,
          url: `${this.baseUrl}${file.file_url}`,
          type: imageFiles[index]?.type || 'image/jpeg',
          size: file.size_bytes,
          tags: [],
          metadata: {},
          created_at: result.upload_time,
        }));
        uploadedAssets.push(...assets);
        if (result.errors && result.errors.length > 0) {
          errors.push(...result.errors);
        }
      } else {
        try { const j = await res.json(); errors.push(j.error || 'Images upload failed'); } catch { errors.push('Images upload failed'); }
      }
    }

    // Handle videos (one by one)
    for (const vf of videoFiles) {
      const form = new FormData();
      form.append('video', vf);
      const res = await fetch(`${this.baseUrl}/videos/upload`, { method: 'POST', body: form });
      if (res.ok) {
        const data = await res.json();
        uploadedAssets.push({
          id: data.filename,
          name: vf.name,
          url: `${this.baseUrl}/videos/${data.filename}`,
          type: vf.type || 'video/mp4',
          size: vf.size,
          tags: [],
          metadata: {},
          created_at: new Date().toISOString(),
        });
      } else {
        try { const j = await res.json(); errors.push(j.error || `Video upload failed: ${vf.name}`); } catch { errors.push(`Video upload failed: ${vf.name}`); }
      }
    }

    return { assets: uploadedAssets, errors: errors.length > 0 ? errors : undefined };
  }

  async getAssets(options?: AssetSearchOptions): Promise<Asset[]> {
    const response = await fetch(`${this.baseUrl}/photos`);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch assets');
    }

    const result = await response.json();
    
    // Convert Flask files to Asset format; infer type by extension and choose the correct route
    let assets: Asset[] = result.photos.map((file: any) => {
      const name: string = file.filename || '';
      const ext = name.split('.').pop()?.toLowerCase() || '';
      const isVideo = ['mp4', 'mov', 'm4v', 'webm'].includes(ext);
      const type = isVideo ? 'video/mp4' : (['png','gif','webp','jpeg','jpg'].includes(ext) ? `image/${ext === 'jpg' ? 'jpeg' : ext}` : 'application/octet-stream');
      const href = `${this.baseUrl}${isVideo ? '/videos/' : '/photos/'}${file.filename}`;
      return {
        id: file.filename,
        name: file.filename,
        url: href,
        type,
        size: file.size_bytes,
        tags: [],
        metadata: {},
        created_at: file.modified_time,
      } as Asset;
    });

    // Apply client-side filtering if options provided
    if (options?.query) {
      const query = options.query.toLowerCase();
      assets = assets.filter(asset => 
        asset.name.toLowerCase().includes(query) ||
        asset.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    if (options?.tags && options.tags.length > 0) {
      assets = assets.filter(asset =>
        options.tags!.every(tag => asset.tags.includes(tag))
      );
    }

    if (options?.limit) {
      assets = assets.slice(options.offset || 0, (options.offset || 0) + options.limit);
    }

    return assets;
  }

  async updateAssetTags(id: string, tags: string[]): Promise<Asset> {
    // Flask backend doesn't support tags yet, so we'll simulate it
    // In a real implementation, you'd extend the Flask API
    const assets = await this.getAssets();
    const asset = assets.find(a => a.id === id);
    
    if (!asset) {
      throw new Error('Asset not found');
    }

    // Return updated asset (simulated)
    return {
      ...asset,
      tags,
      updated_at: new Date().toISOString(),
    };
  }

  async deleteAsset(id: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/photos/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete asset');
    }
  }
}

// Service factory - only Flask backend supported now
export function createAssetService(): AssetService {
  return new FlaskAssetService();
}

// Default service instance
export const assetService = createAssetService();
