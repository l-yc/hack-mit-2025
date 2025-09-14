"use client";

import { useState, useRef, useMemo, useEffect } from 'react';
import { PlusIcon, MagnifyingGlassIcon, XMarkIcon, TagIcon, ArrowPathIcon, TrashIcon } from '@heroicons/react/24/outline';
import { useAppContext } from '@/lib/context';
import { Asset, assetService } from '@/lib/asset-service';

export default function AssetsPage() {
  const {
    assets,
    setAssets,
    searchQuery,
    setSearchQuery,
    selectedTags,
    setSelectedTags
  } = useAppContext();
  
  const [isUploading, setIsUploading] = useState(false);
  const [showTagInput, setShowTagInput] = useState<string | null>(null);
  const [newTag, setNewTag] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [previewAsset, setPreviewAsset] = useState<Asset | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load assets on component mount
  useEffect(() => {
    fetchAssets();
  }, []);

  const fetchAssets = async () => {
    try {
      setIsLoading(true);
      const assets = await assetService.getAssets({ query: searchQuery, tags: selectedTags });
      setAssets(assets);
    } catch (error) {
      console.error('Error fetching assets:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    
    try {
      const result = await assetService.uploadAssets(Array.from(files));
      setAssets([...result.assets, ...assets]);
      
      if (result.errors && result.errors.length > 0) {
        console.warn('Some files failed to upload:', result.errors);
        alert(`Some files failed to upload: ${result.errors.join(', ')}`);
      }
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Error uploading files:', error);
      alert('Failed to upload files. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleAddTag = async (assetId: string) => {
    if (!newTag.trim()) return;

    try {
      const currentAsset = assets.find(a => a.id === assetId);
      if (!currentAsset) return;
      
      const updatedTags = [...currentAsset.tags, newTag.trim()];
      const updatedAsset = await assetService.updateAssetTags(assetId, updatedTags);
      
      setAssets(assets.map(asset => 
        asset.id === assetId ? updatedAsset : asset
      ));
      
      setNewTag('');
      setShowTagInput(null);
    } catch (error) {
      console.error('Error adding tag:', error);
      alert('Failed to add tag. Please try again.');
    }
  };

  const handleRemoveTag = async (assetId: string, tagToRemove: string) => {
    try {
      const asset = assets.find(a => a.id === assetId);
      if (!asset) return;

      const updatedTags = asset.tags.filter(tag => tag !== tagToRemove);
      const updatedAsset = await assetService.updateAssetTags(assetId, updatedTags);
      
      setAssets(assets.map(a => 
        a.id === assetId ? updatedAsset : a
      ));
    } catch (error) {
      console.error('Error removing tag:', error);
      alert('Failed to remove tag. Please try again.');
    }
  };

  const deleteAsset = async (id: string) => {
    try {
      await assetService.deleteAsset(id);
      setAssets(assets.filter(asset => asset.id !== id));
    } catch (error) {
      console.error('Error deleting asset:', error);
      alert('Failed to delete asset. Please try again.');
    }
  };

  // Advanced search filtering
  const filteredAssets = useMemo(() => {
    return assets.filter(asset => {
      const query = searchQuery.toLowerCase();
      
      // Tag filtering - if tags are selected, asset must have ALL selected tags
      if (selectedTags.length > 0) {
        const hasAllTags = selectedTags.every(selectedTag => asset.tags.includes(selectedTag));
        if (!hasAllTags) return false;
      }
      
      // If no search query, return true (already filtered by tags above)
      if (query === '') return true;
      
      // Search in name
      if (asset.name.toLowerCase().includes(query)) return true;
      
      // Search in metadata
      if (asset.metadata.location?.toLowerCase().includes(query)) return true;
      if (asset.metadata.people?.some((person: string) => person.toLowerCase().includes(query))) return true;
      if (asset.metadata.subjects?.some((subject: string) => subject.toLowerCase().includes(query))) return true;
      if (asset.metadata.colors?.some((color: string) => color.toLowerCase().includes(query))) return true;
      if (asset.metadata.mood?.toLowerCase().includes(query)) return true;
      
      // Search in tags
      if (asset.tags.some((tag: string) => tag.toLowerCase().includes(query))) return true;
      
      return false;
    });
  }, [assets, searchQuery, selectedTags]);

  // Get all unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    assets.forEach(asset => {
      asset.tags.forEach(tag => tagSet.add(tag));
    });
    return Array.from(tagSet);
  }, [assets]);

  return (
    <div className="p-8 bg-white min-h-screen overflow-hidden">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Your Assets</h1>
        <p className="mt-2 text-gray-600">
          Upload and manage your photos and videos for content generation.
        </p>
      </div>

      {/* Search and Filter Section */}
      <div className="mb-6 space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by location, people, subjects, colors, mood, or tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-gray-900 placeholder-gray-500"
          />
        </div>

        {/* Tag Filter */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-sm font-medium text-gray-700 flex items-center">
              Filter by tags:
            </span>
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => setSelectedTags(selectedTags.includes(tag) ? selectedTags.filter((t: string) => t !== tag) : [...selectedTags, tag])}
                className={`px-3 py-1 rounded-full text-sm transition-colors cursor-pointer ${
                  selectedTags.includes(tag)
                    ? 'bg-purple-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {tag}
              </button>
            ))}
            <button
              onClick={() => setSelectedTags([])}
              className={`px-2 py bg-gray-500 text-white text-sm rounded-lg hover:bg-gray-600 transition-colors cursor-pointer ${selectedTags.length > 0 ? 'visible' : 'invisible'}`}
            >
              Clear All
            </button>
          </div>
        )}
      </div>

      {/* Asset Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {/* Upload Button */}
        <div className="aspect-square">
          <label
            htmlFor="file-upload"
            className="group cursor-pointer aspect-square bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center hover:bg-gray-100 hover:border-purple-400 transition-colors"
          >
            {isUploading ? (
              <ArrowPathIcon className="h-8 w-8 text-purple-500 animate-spin" />
            ) : (
              <PlusIcon className="h-8 w-8 text-gray-400 group-hover:text-purple-500" />
            )}
            <span className="mt-2 text-xs text-gray-500 group-hover:text-purple-600">
              {isUploading ? 'Uploading...' : 'Add Asset(s)'}
            </span>
            <input
              id="file-upload"
              name="file-upload"
              type="file"
              className="sr-only"
              multiple
              accept="image/*,video/*"
              onChange={handleFileUpload}
              disabled={isUploading}
            />
          </label>
        </div>

        {/* Asset Grid Items */}
      {filteredAssets.map((asset) => (
        <div key={asset.id} className="relative group aspect-square">
          <div className="w-full h-full rounded-lg overflow-hidden bg-gray-100 cursor-pointer" onClick={() => setPreviewAsset(asset)}>
            {asset.type.startsWith('image') ? (
              <img
                src={asset.url}
                alt={asset.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  console.error('Image failed to load:', asset.url);
                  e.currentTarget.style.display = 'none';
                }}
                onLoad={() => console.log('Image loaded successfully:', asset.url)}
              />
            ) : (
              <video
                src={asset.url}
                className="w-full h-full object-cover"
                controls={false}
                muted
              />
            )}
            
            {/* Type badge */}
            <div className="absolute top-2 right-2">
              <span className={`px-2 py-1 rounded text-xs font-medium ${asset.type.startsWith('video') ? 'bg-blue-600 text-white' : 'bg-emerald-600 text-white'}`}>
                {asset.type.startsWith('video') ? 'Video' : 'Photo'}
              </span>
            </div>

            {/* Metadata overlay on hover */}
            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all duration-200 flex flex-col justify-between p-3 opacity-0 group-hover:opacity-80 rounded-lg">
              <div className="flex flex-col space-y-1 text-white text-xs pointer-events-none">
                <div className="flex items-center">
                  <span className="font-medium">📁 {asset.name}</span>
                </div>
                <div className="flex items-center">
                  <span className="font-medium">📏 {asset.metadata.width}x{asset.metadata.height}</span>
                </div>
                <div className="flex items-center">
                  <span className="font-medium">📅 {asset.created_at ? new Date(asset.created_at).toLocaleDateString() : 'Unknown date'}</span>
                </div>
                {asset.metadata.location && (
                  <div className="flex items-center">
                    <span className="font-medium">📍 {asset.metadata.location}</span>
                  </div>
                )}
                {asset.metadata.people && asset.metadata.people.length > 0 && (
                  <div className="flex items-center">
                    <span className="font-medium">👥 {asset.metadata.people.join(', ')}</span>
                  </div>
                )}
                {asset.metadata.subjects && asset.metadata.subjects.length > 0 && (
                  <div className="flex items-center">
                    <span className="font-medium">🏷️ {asset.metadata.subjects.join(', ')}</span>
                  </div>
                )}
                {asset.metadata.mood && (
                  <div className="flex items-center">
                    <span className="font-medium">😊 {asset.metadata.mood}</span>
                  </div>
                )}
              </div>
              
              <div className="flex justify-between items-end pointer-events-auto">
                <button
                  onClick={() => setShowTagInput(showTagInput === asset.id ? null : asset.id)}
                  className="p-1 bg-purple-500 rounded text-white hover:bg-purple-600 transition-colors cursor-pointer"
                  title="Add tag"
                >
                  <TagIcon className="h-3 w-3" />
                </button>
                <button
                  onClick={() => deleteAsset(asset.id)}
                  className="p-1 bg-red-500 rounded text-white hover:bg-red-600 transition-colors cursor-pointer"
                  title="Delete"
                >
                  <TrashIcon className="h-3 w-3" />
                </button>
              </div>
            </div>
            
            {/* Tags */}
            {asset.tags.length > 0 && (
              <div className="absolute top-2 left-2 flex flex-wrap gap-1">
                {asset.tags.slice(0, 2).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-purple-500 text-white text-xs rounded-full flex items-center"
                  >
                    {tag}
                    <button
                      onClick={() => handleRemoveTag(asset.id, tag)}
                      className="ml-1 hover:text-red-200 cursor-pointer"
                    >
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                ))}
                {asset.tags.length > 2 && (
                  <span className="px-2 py-1 bg-gray-500 text-white text-xs rounded-full">
                    +{asset.tags.length - 2}
                  </span>
                )}
              </div>
            )}
            
            {/* Tag Input */}
            {showTagInput === asset.id && (
              <div className="absolute bottom-2 left-2 right-2 bg-white rounded-lg p-2 shadow-lg">
                <div className="relative">
                  <input
                    type="text"
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    placeholder="Add a tag..."
                    className="w-full px-2 py-1 pr-16 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-purple-500 focus:border-purple-500 text-gray-900"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newTag.trim()) {
                        handleAddTag(asset.id);
                      } else if (e.key === 'Escape') {
                        setNewTag('');
                        setShowTagInput(null);
                      }
                    }}
                    autoFocus
                  />
                  <div className="absolute right-1 top-1/2 -translate-y-1/2 flex gap-1">
                    <button
                      onClick={() => {
                        if (newTag.trim()) {
                          handleAddTag(asset.id);
                          setNewTag('');
                          setShowTagInput(null);
                        }
                      }}
                      className="px-2 py-0.5 bg-purple-500 text-white text-xs rounded hover:bg-purple-600 cursor-pointer"
                    >
                      Add
                    </button>
                    <button
                      onClick={() => {
                        setNewTag('');
                        setShowTagInput(null);
                      }}
                      className="px-1 py-0.5 bg-gray-500 text-white text-xs rounded hover:bg-gray-600 cursor-pointer"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-12 mt-8">
          <div className="mx-auto h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center">
            <ArrowPathIcon className="h-6 w-6 text-purple-600 animate-spin" />
          </div>
          <h3 className="mt-4 text-lg font-medium text-gray-900">Loading assets...</h3>
          <p className="mt-2 text-gray-500">
            Fetching your photos and videos from the database.
          </p>
        </div>
      ) : assets.length === 0 && !isUploading && (
        <div className="text-center py-12 mt-8">
          <h3 className="mt-4 text-lg font-medium text-gray-900">No assets yet</h3>
          <p className="mt-2 text-gray-500">
            Click the upload button above to add your first photo or video.
          </p>
        </div>
      )}

      {/* Preview Modal */}
      {previewAsset && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setPreviewAsset(null)}>
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <h3 className="text-lg font-semibold text-gray-900 truncate">{previewAsset.name}</h3>
              <button onClick={() => setPreviewAsset(null)} className="text-gray-500 hover:text-gray-700 cursor-pointer">
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            <div className="p-4 bg-gray-50">
              <div className={`w-full ${previewAsset.type.startsWith('video') ? 'aspect-[9/16] max-w-xs mx-auto' : 'aspect-square max-w-md mx-auto'} bg-black rounded-lg overflow-hidden`}>
                {previewAsset.type.startsWith('video') ? (
                  <video src={previewAsset.url} controls className="w-full h-full object-contain bg-black" />
                ) : (
                  <img src={previewAsset.url} alt={previewAsset.name} className="w-full h-full object-contain bg-black" />
                )}
              </div>
            </div>
            <div className="px-4 pb-4 text-sm text-gray-600">
              <div>Type: {previewAsset.type}</div>
              <div>Size: {(previewAsset.size / 1024).toFixed(1)} KB</div>
              <div>Date: {previewAsset.created_at ? new Date(previewAsset.created_at).toLocaleString() : 'Unknown'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
