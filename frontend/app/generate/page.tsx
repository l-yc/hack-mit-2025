"use client";

import { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon, ArrowDownTrayIcon, ShareIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { useAppContext } from '@/lib/context';
import { Asset } from '@/lib/asset-service';

type Message = {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  assets?: Asset[];
};

type ContentType = {
  id: string;
  name: string;
  description: string;
  purpose: string;
  target: string;
  dimensions: string;
  icon: string;
};

const contentTypes: ContentType[] = [
  {
    id: 'instagram-post',
    name: 'Instagram Post',
    description: 'Square format post for your Instagram feed',
    purpose: '',
    target: '',
    dimensions: '1080x1080px',
    icon: '📸'
  },
  {
    id: 'instagram-story',
    name: 'Instagram Story',
    description: 'Vertical story content that disappears after 24 hours',
    purpose: '',
    target: '',
    dimensions: '1080x1920px',
    icon: '📱'
  },
  {
    id: 'instagram-reel',
    name: 'Instagram Reel',
    description: 'Short-form vertical video content',
    purpose: '',
    target: '',
    dimensions: '1080x1920px (15-90 seconds)',
    icon: '🎬'
  }
];

export default function GenerateContentPage() {
  const {
    selectedContentType,
    setSelectedContentType,
    messages,
    setMessages,
    chatFlow,
    setChatFlow,
    selectedAssets,
    setSelectedAssets,
    postCaption,
    setPostCaption,
    userPurpose,
    setUserPurpose,
    userTarget,
    setUserTarget,
    selectedProject,
    setSelectedProject,
    currentImageIndex,
    setCurrentImageIndex,
    assets
  } = useAppContext();

  const [showContentTypes, setShowContentTypes] = useState(!selectedContentType);
  const [inputMessage, setInputMessage] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load assets from Supabase
  const [availableAssets, setAvailableAssets] = useState<Asset[]>([]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load assets from API on component mount
  useEffect(() => {
    const fetchAssets = async () => {
      try {
        const response = await fetch('/api/assets');
        const data = await response.json();
        if (data.assets) {
          // Convert Supabase assets to Generate page format
          const convertedAssets = data.assets.map((asset: any) => ({
            id: asset.id.toString(),
            name: asset.name,
            url: asset.url,
            type: asset.type.startsWith('image') ? 'image' : 'video'
          }));
          setAvailableAssets(convertedAssets);
        }
      } catch (error) {
        console.error('Error fetching assets:', error);
      }
    };

    fetchAssets();
  }, []);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputMessage;
    setInputMessage('');
    setIsGenerating(true);

    // Simulate AI response based on chat flow
    await new Promise(resolve => setTimeout(resolve, 1500));

    let aiResponse: Message;

    if (chatFlow === 'purpose') {
      setUserPurpose(currentInput);
      aiResponse = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Great! Now, who is your target audience for this Instagram post? (e.g., young professionals, fitness enthusiasts, food lovers, etc.)',
        timestamp: new Date(),
      };
      setChatFlow('project');
    } else if (chatFlow === 'project') {
      setUserTarget(currentInput);
      aiResponse = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Perfect! What project or theme should I choose assets from? (e.g., vacation photos, product shots, lifestyle content, etc.)',
        timestamp: new Date(),
      };
      setChatFlow('generating');
    } else {
      setSelectedProject(currentInput);
      setChatFlow('complete');
      
      // Auto-select relevant assets and generate content
      const relevantAssets = availableAssets.slice(0, 3); // Mock selection
      setSelectedAssets(relevantAssets);
      
      const generatedCaption = `✨ ${userPurpose}\n\nPerfect for ${userTarget} who love authentic moments! This ${selectedProject} content really captures the essence of what we're all about.\n\n#${selectedProject.replace(/\s+/g, '').toLowerCase()} #authentic #lifestyle #inspiration`;
      setPostCaption(generatedCaption);
      
      aiResponse = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `Perfect! I've selected ${relevantAssets.length} assets from your ${selectedProject} and created a draft post. You can see the preview in the center pane and edit the caption as needed.`,
        timestamp: new Date(),
      };
    }

    setMessages(prev => [...prev, aiResponse]);
    setIsGenerating(false);
  };

  const generateMockResponse = (prompt: string, assets: Asset[]) => {
    const responses = [
      `🌟 Just captured this incredible moment! ${prompt ? `Here's what I think: ${prompt}` : 'The lighting and composition are absolutely perfect.'}\n\n✨ Sometimes the best shots happen when you least expect them. This one definitely tells a story!\n\n#photography #moment #captured #beautiful #memories`,
      `📸 This shot is giving me all the feels! ${prompt || 'The colors and mood are just *chef\'s kiss*'}\n\nThere's something magical about finding beauty in everyday moments. What do you all think?\n\n#photooftheday #vibes #aesthetic #mood #inspiration`,
      `Wow! ${prompt || 'This is exactly the kind of content that stops the scroll.'} 🔥\n\nThe way the light hits here is just... *perfection*. Sometimes you just know when you've captured something special.\n\n#contentcreator #photography #lightroom #edit #creative`
    ];
    
    return responses[Math.floor(Math.random() * responses.length)];
  };

  const toggleAssetSelection = (asset: Asset) => {
    setSelectedAssets(prev => {
      const exists = prev.find(a => a.id === asset.id);
      if (exists) {
        return prev.filter(a => a.id !== asset.id);
      } else {
        return [...prev, asset];
      }
    });
  };

  const downloadContent = () => {
    if (!editableContent) return;
    
    const element = document.createElement('a');
    const file = new Blob([editableContent], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${selectedContentType?.name || 'content'}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const postToInstagram = () => {
    // This would integrate with Instagram's API
    alert('Instagram posting feature would be implemented here with proper API integration');
  };

  const initializeChatFlow = (contentType: ContentType) => {
    setSelectedContentType(contentType);
    setShowContentTypes(false);
    setChatFlow('purpose');
    setMessages([
      {
        id: '1',
        type: 'assistant',
        content: `Great choice! Let's create an amazing ${contentType.name}. First, what's the main purpose or message of this post? (e.g., promote a product, share an experience, inspire your audience, etc.)`,
        timestamp: new Date(),
      }
    ]);
  };

  const [isSliding, setIsSliding] = useState(false);
  const [slideDirection, setSlideDirection] = useState<'left' | 'right' | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragOffset, setDragOffset] = useState(0);

  const nextImage = () => {
    if (isSliding) return;
    setIsSliding(true);
    setSlideDirection('left');
    setTimeout(() => {
      setCurrentImageIndex((prev) => (prev + 1) % selectedAssets.length);
      setSlideDirection(null);
      setIsSliding(false);
    }, 300);
  };

  const prevImage = () => {
    if (isSliding) return;
    setIsSliding(true);
    setSlideDirection('right');
    setTimeout(() => {
      setCurrentImageIndex((prev) => (prev - 1 + selectedAssets.length) % selectedAssets.length);
      setSlideDirection(null);
      setIsSliding(false);
    }, 300);
  };

  const handleDragStart = (e: React.MouseEvent | React.TouchEvent) => {
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    setDragStart(clientX);
    setDragOffset(0);
  };

  const handleDragMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (dragStart === null) return;
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const offset = clientX - dragStart;
    setDragOffset(offset);
  };

  const handleDragEnd = () => {
    if (dragStart === null) return;
    
    const threshold = 50; // minimum drag distance to trigger navigation
    if (Math.abs(dragOffset) > threshold) {
      if (dragOffset > 0) {
        prevImage();
      } else {
        nextImage();
      }
    }
    
    setDragStart(null);
    setDragOffset(0);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Middle - Content Creation Flow */}
      <div className="flex-1 flex flex-col bg-white border-r border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {selectedContentType ? selectedContentType.name : 'Choose Content Type'}
              </h2>
              <p className="text-sm text-gray-500">
                {selectedContentType ? 'Create your Instagram post' : 'Select the type of content you want to create'}
              </p>
            </div>
            <div className="flex items-center space-x-2">
              {selectedContentType && (
                <button
                  onClick={() => {
                    setSelectedContentType(null);
                    setShowContentTypes(true);
                    setMessages([]);
                    setPostCaption('');
                    setSelectedAssets([]);
                    setChatFlow('purpose');
                  }}
                  className="px-4 py-2 text-sm text-purple-600 hover:text-purple-700 border border-purple-300 rounded-lg hover:bg-purple-50 cursor-pointer"
                >
                  Change Type
                </button>
              )}
              {selectedContentType && chatFlow === 'complete' && selectedAssets.length > 0 && (
                <>
                  <button
                    onClick={downloadContent}
                    className="flex items-center px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                    Save
                  </button>
                  <button
                    onClick={postToInstagram}
                    className="flex items-center px-3 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors cursor-pointer"
                  >
                    <ShareIcon className="h-4 w-4 mr-1" />
                    Share
                  </button>
                </>
              )} 
            </div>
          </div>
        </div>
        
        <div className="flex-1 p-6 overflow-y-auto">
          {showContentTypes && !selectedContentType ? (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">What would you like to create?</h3>
                <p className="text-gray-600">Choose a content type to get started with AI-powered generation</p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {contentTypes.map((contentType) => (
                  <div
                    key={contentType.id}
                    className="bg-white border-2 border-gray-200 rounded-xl p-6 hover:border-purple-300 hover:shadow-lg transition-all cursor-pointer"
                    onClick={() => initializeChatFlow(contentType)}
                  >
                    <div className="text-center">
                      <div className="text-4xl mb-4">{contentType.icon}</div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">{contentType.name}</h3>
                      <p className="text-gray-600 text-sm">{contentType.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : chatFlow === 'complete' && selectedAssets.length > 0 ? (
            <div className="space-y-6">

              {/* Image Carousel */}
              <div className="bg-gray-50 rounded-lg p-6">
                <div className="relative">
                  <div 
                    className="aspect-square bg-white rounded-lg overflow-hidden border border-gray-200 max-w-md mx-auto cursor-grab active:cursor-grabbing"
                    onMouseDown={handleDragStart}
                    onMouseMove={handleDragMove}
                    onMouseUp={handleDragEnd}
                    onMouseLeave={handleDragEnd}
                    onTouchStart={handleDragStart}
                    onTouchMove={handleDragMove}
                    onTouchEnd={handleDragEnd}
                  >
                    {selectedAssets.length > 0 && (
                      <div className="relative w-full h-full overflow-hidden">
                        {/* Image Container - slides as one unit */}
                        <div 
                          className={`flex ${slideDirection ? 'transition-transform duration-300 ease-out' : ''}`}
                          style={{
                            transform: `translateX(calc(-33.333% + ${dragOffset * 0.5}px)) ${
                              slideDirection === 'left' ? 'translateX(-33.333%)' : 
                              slideDirection === 'right' ? 'translateX(33.333%)' : ''
                            }`,
                            width: '300%',
                            height: '100%'
                          }}
                        >
                          {/* Previous Image */}
                          <div className="flex-shrink-0" style={{ width: '33.333%', height: '100%' }}>
                            <img
                              src={selectedAssets[(currentImageIndex - 1 + selectedAssets.length) % selectedAssets.length]?.url || '/api/placeholder/400/400'}
                              alt="Previous image"
                              className="w-full h-full object-cover select-none"
                              draggable={false}
                            />
                          </div>
                          
                          {/* Current Image */}
                          <div className="flex-shrink-0" style={{ width: '33.333%', height: '100%' }}>
                            <img
                              src={selectedAssets[currentImageIndex]?.url || '/api/placeholder/400/400'}
                              alt={selectedAssets[currentImageIndex]?.name || 'Selected asset'}
                              className="w-full h-full object-cover select-none"
                              draggable={false}
                            />
                          </div>
                          
                          {/* Next Image */}
                          <div className="flex-shrink-0" style={{ width: '33.333%', height: '100%' }}>
                            <img
                              src={selectedAssets[(currentImageIndex + 1) % selectedAssets.length]?.url || '/api/placeholder/400/400'}
                              alt="Next image"
                              className="w-full h-full object-cover select-none"
                              draggable={false}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Navigation arrows */}
                  {selectedAssets.length > 1 && (
                    <>
                      <button
                        onClick={prevImage}
                        disabled={isSliding}
                        className="absolute left-2 top-1/2 transform -translate-y-1/2 bg-gray-100 hover:bg-gray-200 p-2 transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed rounded-md"
                      >
                        <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                      </button>
                      <button
                        onClick={nextImage}
                        disabled={isSliding}
                        className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-gray-100 hover:bg-gray-200 p-2 transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed rounded-md"
                      >
                        <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </>
                  )}
                  
                  {/* Image indicators */}
                  {selectedAssets.length > 1 && (
                    <div className="flex justify-center mt-4 space-x-2">
                      {selectedAssets.map((_, index) => (
                        <button
                          key={index}
                          onClick={() => setCurrentImageIndex(index)}
                          className={`w-2 h-2 rounded-full transition-colors cursor-pointer ${
                            index === currentImageIndex ? 'bg-purple-500' : 'bg-gray-300'
                          }`}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
              
              {/* Caption Editor */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Post Caption
                </label>
                <textarea
                  value={postCaption}
                  onChange={(e) => setPostCaption(e.target.value)}
                  className="w-full h-32 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none text-gray-900 placeholder-gray-500"
                  placeholder="Write your caption here..."
                  style={{ color: '#1f2937' }}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {postCaption.length} characters
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-center">
              <div>
                <div className="mx-auto h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center">
                  <span className="text-2xl">{selectedContentType?.icon}</span>
                </div>
                <h3 className="mt-4 text-lg font-medium text-gray-900">Ready to create {selectedContentType?.name}</h3>
                <p className="mt-2 text-gray-500">
                  Chat with the AI to generate content for your {selectedContentType?.name.toLowerCase()}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right - Chat Interface */}
      {selectedContentType && (
        <div className="w-96 flex flex-col bg-white">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">AI Assistant</h3>
            <p className="text-sm text-gray-500">Chat to generate content</p>
          </div>


          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs rounded-lg px-3 py-2 ${
                    message.type === 'user'
                      ? 'bg-purple-500 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.assets && message.assets.length > 0 && (
                    <div className="mb-2 flex space-x-1">
                      {message.assets.map((asset) => (
                        <div key={asset.id} className="w-8 h-8 bg-white/20 rounded flex items-center justify-center">
                          <span className="text-xs">{asset.type === 'image' ? '📷' : '🎥'}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-sm whitespace-pre-line">{message.content}</p>
                  <p className={`text-xs mt-1 ${message.type === 'user' ? 'text-purple-100' : 'text-gray-500'}`}>
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
            
            {isGenerating && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg px-3 py-2">
                  <div className="flex items-center space-x-2">
                    <ArrowPathIcon className="h-4 w-4 text-purple-500 animate-spin" />
                    <span className="text-sm text-gray-600">Generating content...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-200">
            <div className="flex space-x-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Describe the content you want to generate..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm text-gray-900 placeholder-gray-500"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() && selectedAssets.length === 0}
                className="px-3 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                <PaperAirplaneIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
