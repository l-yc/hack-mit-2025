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
    const formData = new FormData();
    
    if (files.length === 1) {
      // Compress image before upload
      const compressedFile = files[0].type.startsWith('image/') 
        ? await this.compressImage(files[0])
        : files[0];
      formData.append('photo', compressedFile);
      
      const response = await fetch(`${this.baseUrl}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Upload failed');
      }

      const result = await response.json();
      
      // Convert Flask response to Asset format
      const asset: Asset = {
        id: result.filename, // Use filename as ID for Flask backend
        name: result.original_filename,
        url: `${this.baseUrl}${result.file_url}`,
        type: files[0].type,
        size: result.size_bytes,
        tags: [],
        metadata: {},
        created_at: result.upload_time,
      };

      return { assets: [asset] };
    } else {
      // Multiple file upload - compress each image
      const compressedFiles = await Promise.all(
        files.map(file => 
          file.type.startsWith('image/') 
            ? this.compressImage(file)
            : Promise.resolve(file)
        )
      );
      compressedFiles.forEach(file => formData.append('photos', file));
      
      const response = await fetch(`${this.baseUrl}/upload/multiple`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Upload failed');
      }

      const result = await response.json();
      
      const assets: Asset[] = result.uploaded_files.map((file: any, index: number) => ({
        id: file.filename,
        name: file.original_filename,
        url: `${this.baseUrl}${file.file_url}`,
        type: files[index]?.type || 'image/jpeg',
        size: file.size_bytes,
        tags: [],
        metadata: {},
        created_at: result.upload_time,
      }));

      return { 
        assets,
        errors: result.errors?.length > 0 ? result.errors : undefined
      };
    }
  }

  async getAssets(options?: AssetSearchOptions): Promise<Asset[]> {
    const response = await fetch(`${this.baseUrl}/photos`);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch assets');
    }

    const result = await response.json();
    
    // Convert Flask photos to Asset format
    let assets: Asset[] = result.photos.map((photo: any) => ({
      id: photo.filename,
      name: photo.filename,
      url: `${this.baseUrl}${photo.file_url}`,
      type: 'image/jpeg', // Default type since Flask doesn't store this
      size: photo.size_bytes,
      tags: [], // Flask backend doesn't store tags yet
      metadata: {},
      created_at: photo.modified_time,
    }));

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
