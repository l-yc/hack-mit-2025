"use client";

import { useState, useMemo } from 'react';
import { PlusIcon, TrashIcon, ArrowPathIcon, MagnifyingGlassIcon, TagIcon, XMarkIcon } from '@heroicons/react/24/outline';

type Asset = {
  id: string;
  name: string;
  url: string;
  type: 'image' | 'video';
  createdAt: Date;
  tags: string[];
  metadata: {
    location?: string;
    people?: string[];
    subjects?: string[];
    colors?: string[];
    mood?: string;
  };
};

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [showTagInput, setShowTagInput] = useState<string | null>(null);
  const [newTag, setNewTag] = useState('');

  // Mock data with enhanced metadata
  const mockMetadata = [
    { location: 'San Francisco', people: ['John', 'Sarah'], subjects: ['sunset', 'cityscape'], colors: ['orange', 'blue'], mood: 'peaceful' },
    { location: 'New York', people: ['Mike'], subjects: ['street', 'architecture'], colors: ['gray', 'black'], mood: 'urban' },
    { location: 'Paris', people: ['Emma', 'Lisa'], subjects: ['food', 'restaurant'], colors: ['warm', 'brown'], mood: 'cozy' },
  ];

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    
    // Simulate file upload
    const newAssets: Asset[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileType = file.type.startsWith('image/') ? 'image' : 'video';
      const randomMetadata = mockMetadata[Math.floor(Math.random() * mockMetadata.length)];
      
      newAssets.push({
        id: Math.random().toString(36).substring(2, 9),
        name: file.name,
        url: URL.createObjectURL(file),
        type: fileType,
        createdAt: new Date(),
        tags: [],
        metadata: randomMetadata,
      });
    }

    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setAssets(prev => [...prev, ...newAssets]);
    setIsUploading(false);
  };

  const deleteAsset = (id: string) => {
    setAssets(prev => prev.filter(asset => asset.id !== id));
  };

  const addTagToAsset = (assetId: string, tag: string) => {
    if (!tag.trim()) return;
    setAssets(prev => prev.map(asset => 
      asset.id === assetId 
        ? { ...asset, tags: [...asset.tags, tag.trim()] }
        : asset
    ));
    setNewTag('');
    setShowTagInput(null);
  };

  const removeTagFromAsset = (assetId: string, tagToRemove: string) => {
    setAssets(prev => prev.map(asset => 
      asset.id === assetId 
        ? { ...asset, tags: asset.tags.filter(tag => tag !== tagToRemove) }
        : asset
    ));
  };

  // Advanced search filtering
  const filteredAssets = useMemo(() => {
    return assets.filter(asset => {
      const query = searchQuery.toLowerCase();
      
      // Search in name
      if (asset.name.toLowerCase().includes(query)) return true;
      
      // Search in metadata
      if (asset.metadata.location?.toLowerCase().includes(query)) return true;
      if (asset.metadata.people?.some(person => person.toLowerCase().includes(query))) return true;
      if (asset.metadata.subjects?.some(subject => subject.toLowerCase().includes(query))) return true;
      if (asset.metadata.colors?.some(color => color.toLowerCase().includes(query))) return true;
      if (asset.metadata.mood?.toLowerCase().includes(query)) return true;
      
      // Search in tags
      if (asset.tags.some(tag => tag.toLowerCase().includes(query))) return true;
      
      // Tag filtering
      if (selectedTags.length > 0) {
        return selectedTags.every(selectedTag => asset.tags.includes(selectedTag));
      }
      
      return query === '';
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
    <div className="p-8 bg-white min-h-full">
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
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm"
          />
        </div>

        {/* Tag Filter */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-sm font-medium text-gray-700 flex items-center">
              <TagIcon className="h-4 w-4 mr-1" />
              Filter by tags:
            </span>
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => {
                  setSelectedTags(prev => 
                    prev.includes(tag) 
                      ? prev.filter(t => t !== tag)
                      : [...prev, tag]
                  );
                }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  selectedTags.includes(tag)
                    ? 'bg-purple-100 text-purple-800 border border-purple-300'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
                }`}
              >
                {tag}
              </button>
            ))}
            {selectedTags.length > 0 && (
              <button
                onClick={() => setSelectedTags([])}
                className="px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-300 hover:bg-red-200"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Search Results Info */}
        {(searchQuery || selectedTags.length > 0) && (
          <div className="text-sm text-gray-600">
            Found {filteredAssets.length} asset{filteredAssets.length !== 1 ? 's' : ''}
            {searchQuery && ` matching "${searchQuery}"`}
            {selectedTags.length > 0 && ` with tags: ${selectedTags.join(', ')}`}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
        {/* Upload Button - First Grid Item */}
        <div className="relative group">
          <label
            htmlFor="file-upload"
            className={`aspect-square flex flex-col items-center justify-center border-2 border-dashed rounded-lg cursor-pointer transition-all ${
              isUploading 
                ? 'border-purple-300 bg-purple-50' 
                : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50'
            }`}
          >
            {isUploading ? (
              <ArrowPathIcon className="h-8 w-8 text-purple-500 animate-spin" />
            ) : (
              <PlusIcon className="h-8 w-8 text-gray-400 group-hover:text-purple-500" />
            )}
            <span className="mt-2 text-xs text-gray-500 group-hover:text-purple-600">
              {isUploading ? 'Uploading...' : 'Add Asset'}
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
            <div className="w-full h-full rounded-lg overflow-hidden bg-gray-100">
              {asset.type === 'image' ? (
                <img
                  src={asset.url}
                  alt={asset.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <video
                  src={asset.url}
                  className="w-full h-full object-cover"
                  controls={false}
                  muted
                />
              )}
              
              {/* Metadata overlay on hover */}
              <div className="absolute inset-0 bg-black bg-opacity-75 opacity-0 group-hover:opacity-100 transition-opacity p-2 flex flex-col justify-between text-white text-xs">
                <div className="space-y-1">
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
                
                <div className="flex justify-between items-end">
                  <button
                    onClick={() => setShowTagInput(showTagInput === asset.id ? null : asset.id)}
                    className="p-1 bg-purple-500 rounded text-white hover:bg-purple-600 transition-colors"
                    title="Add tag"
                  >
                    <TagIcon className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => deleteAsset(asset.id)}
                    className="p-1 bg-red-500 rounded text-white hover:bg-red-600 transition-colors"
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
                        onClick={() => removeTagFromAsset(asset.id, tag)}
                        className="ml-1 hover:text-red-200"
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
              
              {/* Tag input */}
              {showTagInput === asset.id && (
                <div className="absolute bottom-2 left-2 right-2">
                  <div className="flex gap-1">
                    <input
                      type="text"
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          addTagToAsset(asset.id, newTag);
                        }
                      }}
                      placeholder="Add tag..."
                      className="flex-1 px-2 py-1 text-xs border rounded text-black"
                      autoFocus
                    />
                    <button
                      onClick={() => addTagToAsset(asset.id, newTag)}
                      className="px-2 py-1 bg-purple-500 text-white text-xs rounded hover:bg-purple-600"
                    >
                      Add
                    </button>
                  </div>
                </div>
              )}
              
              {/* Asset info */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
                <p className="text-xs font-medium text-white truncate">{asset.name}</p>
                <p className="text-xs text-gray-300">
                  {asset.type === 'image' ? '📷' : '🎥'} {asset.createdAt.toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {assets.length === 0 && !isUploading && (
        <div className="text-center py-12 mt-8">
          <div className="mx-auto h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center">
            <PlusIcon className="h-6 w-6 text-purple-600" />
          </div>
          <h3 className="mt-4 text-lg font-medium text-gray-900">No assets yet</h3>
          <p className="mt-2 text-gray-500">
            Click the upload button to add your first photo or video.
          </p>
        </div>
      )}
    </div>
  );
}
