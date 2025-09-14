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

type Agent = {
  name: string;
  path: string;
  description: string;
};

type ChatFlow = 'subject' | 'agent' | 'photos' | 'generating' | 'complete';

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
    selectedAssets,
    setSelectedAssets,
    postCaption,
    setPostCaption,
    currentImageIndex,
    setCurrentImageIndex,
    assets
  } = useAppContext();

  // New state for the parameter collection flow
  const [chatFlow, setChatFlow] = useState<ChatFlow>('subject');
  const [subject, setSubject] = useState<string>('');
  const [selectedAgents, setSelectedAgents] = useState<Agent[]>([]);
  const [numPhotos, setNumPhotos] = useState<number>(3);
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);

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

  // Fetch available agents
  const fetchAgents = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_FLASK_BACKEND_URL || 'http://localhost:6741'}/agents`);
      const data = await response.json();
      if (data.agents) {
        setAvailableAgents(data.agents);
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

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
    fetchAgents();
  }, []);

  const handleAgentClick = (agent: Agent) => {
    setSelectedAgents(prev => {
      const exists = prev.find(a => a.name === agent.name);
      if (exists) {
        return prev.filter(a => a.name !== agent.name);
      } else {
        return [...prev, agent];
      }
    });
  };

  const handleContinue = () => {
    if (selectedAgents.length > 0) {
      // Add user message showing the selected agents
      const agentNames = selectedAgents.map(a => a.name.replace('.md', '')).join(', ');
      const userMessage: Message = {
        id: Date.now().toString(),
        type: 'user',
        content: agentNames,
        timestamp: new Date(),
      };
      
      // Different messaging for Stories vs Posts/Reels
      const continueMessage = selectedContentType?.id === 'instagram-story'
        ? `Excellent! You've selected ${agentNames} for your story. For Instagram Stories, I recommend 3-7 photos to create a compelling narrative sequence. How many photos would you like? (3-7 recommended)`
        : selectedContentType?.id === 'instagram-reel'
          ? `Great choice: ${agentNames}. How many video clips would you like me to use? (1-5)`
          : `Perfect! You've selected ${agentNames}. Now, how many photos would you like me to select? (1-10)`;
      
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: continueMessage,
        timestamp: new Date(),
      };
      
      // Add both user and AI messages
      setMessages([...messages, userMessage, aiResponse]);
      setChatFlow('photos');
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    // Create updated messages array with user message
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    
    const currentInput = inputMessage;
    setInputMessage('');
    setIsGenerating(true);

    // Simulate AI response based on chat flow
    await new Promise(resolve => setTimeout(resolve, 1500));

    let aiResponse: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: 'I understand. Please try again.',
      timestamp: new Date(),
    };

    if (chatFlow === 'subject') {
      setSubject(currentInput);
      
      // Different flows based on content type
      if (selectedContentType?.id === 'instagram-story') {
        aiResponse = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `Perfect! Creating a story about "${currentInput}". For Instagram Stories, we'll create a sequence that tells a compelling narrative. Which AI agent would you like to use for photo selection?`,
          timestamp: new Date(),
        };
      } else if (selectedContentType?.id === 'instagram-reel') {
        aiResponse = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `Awesome! We'll create a Reel about "${currentInput}". Choose agents to guide the style, then tell me how many video clips to use (1-5).`,
          timestamp: new Date(),
        };
      } else {
        aiResponse = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: 'Great! Now, which AI agent would you like to use for photo selection? Choose from the available agents below:',
          timestamp: new Date(),
        };
      }
      setChatFlow('agent');
    } else if (chatFlow === 'agent') {
      // Check if user wants to continue
      if (currentInput.toLowerCase().includes('continue') || currentInput.toLowerCase().includes('done')) {
        if (selectedAgents.length > 0) {
          const agentNames = selectedAgents.map(a => a.name.replace('.md', '')).join(', ');
          
          // Different messaging for Stories vs Posts/Reels
          if (selectedContentType?.id === 'instagram-story') {
            aiResponse = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: `Excellent! You've selected ${agentNames} for your story. For Instagram Stories, I recommend 3-7 photos to create a compelling narrative sequence. How many photos would you like? (3-7 recommended)`,
              timestamp: new Date(),
            };
          } else if (selectedContentType?.id === 'instagram-reel') {
            aiResponse = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: `Great choice: ${agentNames}. How many video clips would you like me to use? (1-5)`,
              timestamp: new Date(),
            };
          } else {
            aiResponse = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: `Perfect! You've selected ${agentNames}. Now, how many photos would you like me to select? (1-10)`,
              timestamp: new Date(),
            };
          }
          setChatFlow('photos');
        } else {
          aiResponse = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: 'Please select at least one agent before continuing.',
            timestamp: new Date(),
          };
        }
      } else {
        // Try to find and toggle agent selection
        const agent = availableAgents.find(a => 
          a.name.toLowerCase().includes(currentInput.toLowerCase()) ||
          a.name.replace('.md', '').toLowerCase().includes(currentInput.toLowerCase())
        );
        
        if (agent) {
          // Toggle agent selection
          setSelectedAgents(prev => {
            const exists = prev.find(a => a.name === agent.name);
            if (exists) {
              return prev.filter(a => a.name !== agent.name);
            } else {
              return [...prev, agent];
            }
          });
          
          const isSelected = selectedAgents.some(a => a.name === agent.name);
          const action = isSelected ? 'removed' : 'added';
          const currentCount = selectedAgents.length + (isSelected ? -1 : 1);
          
          aiResponse = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: `Great! I've ${action} ${agent.name.replace('.md', '')} ${isSelected ? 'from' : 'to'} your selection. You now have ${currentCount} agent${currentCount !== 1 ? 's' : ''} selected. Type "continue" when you're ready to proceed.`,
            timestamp: new Date(),
          };
        } else {
          aiResponse = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: 'Please select agents by clicking on them above, or type "continue" when you\'re ready to proceed.',
            timestamp: new Date(),
          };
        }
      }
    } else if (chatFlow === 'photos') {
      const photoCount = parseInt(currentInput);
      
      // Different validation for Stories vs Posts/Reels
      const isReel = selectedContentType?.id === 'instagram-reel';
      const isValidCount = selectedContentType?.id === 'instagram-story' 
        ? (photoCount >= 1 && photoCount <= 10) // Stories can have 1-10 photos
        : isReel
          ? (photoCount >= 1 && photoCount <= 5) // Reels: 1-5 clips
          : (photoCount >= 1 && photoCount <= 10);
      
      if (isValidCount) {
        setNumPhotos(photoCount);
        setChatFlow('generating');
        
        // For reels: select videos from assets; otherwise call /select for photos
        try {
          if (isReel) {
            // Fetch available videos from backend
            const vidsRes = await fetch(`${process.env.NEXT_PUBLIC_FLASK_BACKEND_URL || 'http://localhost:6741'}/videos`);
            const vidsJson = await vidsRes.json();
            const availableVideos = (vidsJson?.videos || []).map((v: any) => ({
              id: v.filename,
              name: v.filename,
              url: `${process.env.NEXT_PUBLIC_FLASK_BACKEND_URL || 'http://localhost:6741'}${v.file_url}`,
              type: 'video/mp4',
              size: v.size_bytes,
              tags: [],
              metadata: {},
              created_at: v.modified_time,
            }));
            if (availableVideos.length === 0) {
              aiResponse = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: 'I could not find any uploaded videos. Please upload some clips in the Assets tab and try again.',
                timestamp: new Date(),
              };
              setChatFlow('photos');
            } else {
              const chosen = availableVideos.slice(0, photoCount);
              setSelectedAssets(chosen as any);
              aiResponse = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: `Selected ${chosen.length} video clip(s) for your Reel. You can preview them above.`,
                timestamp: new Date(),
              };
              setChatFlow('complete');
            }
          } else {
            const response = await fetch(`${process.env.NEXT_PUBLIC_FLASK_BACKEND_URL || 'http://localhost:6741'}/select`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              n: photoCount,
              post_type: `${selectedContentType?.name || 'Post'} about ${subject}`,
              agents: selectedAgents.map(agent => agent.path),
              auto_cleanup: false,
            }),
            });

          const data = await response.json();
          
          if (data.selected_photos && data.selected_photos.length > 0) {
            // Convert selected photos to Asset format
            const selectedPhotos = data.selected_photos.map((photo: any) => ({
              id: photo.filename,
              name: photo.filename,
              url: `${process.env.NEXT_PUBLIC_FLASK_BACKEND_URL || 'http://localhost:6741'}/photos/${photo.filename}`,
              type: 'image/jpeg',
              size: photo.size_bytes,
              tags: [],
              metadata: {},
              created_at: photo.modified_time,
            }));
            
            setSelectedAssets(selectedPhotos);
            
            // Generate caption from API response post_caption
            let generatedCaption = '';
            if (data.post_caption) {
              try {
                // Use the single post caption from the backend
                if (typeof data.post_caption === 'object' && data.post_caption.text) {
                  generatedCaption = data.post_caption.text;
                } else if (typeof data.post_caption === 'string') {
                  generatedCaption = data.post_caption;
                }
              } catch (error) {
                console.error('Error parsing post_caption:', error);
              }
            }
            
            // Set the generated caption
            if (generatedCaption) {
              setPostCaption(generatedCaption);
            }
            
            const agentNames = selectedAgents.map(a => a.name.replace('.md', '')).join(', ');
            
            // Different success messages for Stories vs Posts
            const successMessage = selectedContentType?.id === 'instagram-story'
              ? `Perfect! I've created a ${selectedPhotos.length}-photo story sequence about "${subject}" using ${agentNames}. The photos are arranged to tell a compelling narrative - perfect for your Instagram Story! I've also generated captions for each photo.`
              : `Excellent! I've selected ${selectedPhotos.length} photos using ${agentNames} for your ${subject} content. I've also generated captions for you - you can see them in the caption field above and edit as needed.`;
            
            aiResponse = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: successMessage,
              timestamp: new Date(),
            };
            setChatFlow('complete');
          } else {
            aiResponse = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: 'Sorry, I couldn\'t find any suitable photos. Please try again or check if there are photos in the directory.',
              timestamp: new Date(),
            };
            setChatFlow('photos');
          }
          }
        } catch (error) {
          console.error('Error calling /select API:', error);
          aiResponse = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: 'Sorry, there was an error selecting photos. Please try again.',
            timestamp: new Date(),
          };
          setChatFlow('photos');
        }
      } else {
        // Different error messages for Stories vs Posts/Reels
        const errorMessage = selectedContentType?.id === 'instagram-story'
          ? 'Please enter a number between 1 and 10. For Stories, I recommend 3-7 photos for the best narrative flow.'
          : isReel
            ? 'Please enter a number between 1 and 5 for the number of clips.'
            : 'Please enter a number between 1 and 10 for the number of photos.';
          
        aiResponse = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: errorMessage,
          timestamp: new Date(),
        };
      }
    }

    // Add AI response to the updated messages (which includes the user message)
    setMessages([...updatedMessages, aiResponse]);
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
    const exists = selectedAssets.find(a => a.id === asset.id);
    if (exists) {
      setSelectedAssets(selectedAssets.filter(a => a.id !== asset.id));
    } else {
      setSelectedAssets([...selectedAssets, asset]);
    }
  };

  const downloadContent = () => {
    if (!postCaption) return;
    
    const element = document.createElement('a');
    const file = new Blob([postCaption], { type: 'text/plain' });
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
    setSelectedContentType(contentType as any);
    setShowContentTypes(false);
    setChatFlow('subject');
    setMessages([
      {
        id: '1',
        type: 'assistant',
        content: `Great choice! Let's create an amazing ${contentType.name}. First, what subject or theme would you like to focus on? (e.g., nature, food, travel, fashion, etc.)`,
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
      setCurrentImageIndex((currentImageIndex + 1) % selectedAssets.length);
      setSlideDirection(null);
      setIsSliding(false);
    }, 300);
  };

  const prevImage = () => {
    if (isSliding) return;
    setIsSliding(true);
    setSlideDirection('right');
    setTimeout(() => {
      setCurrentImageIndex((currentImageIndex - 1 + selectedAssets.length) % selectedAssets.length);
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
                    setChatFlow('subject');
                    setSubject('');
                    setSelectedAgents([]);
                    setNumPhotos(3);
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
          ) : (chatFlow === 'complete' || chatFlow === 'generating') && selectedAssets.length > 0 ? (
            <div className="space-y-6">

              {/* Image Carousel */}
              <div className="bg-gray-50 rounded-lg p-6">
                <div className="relative">
                  <div 
                    className={`${selectedContentType?.id === 'instagram-story' ? 'aspect-[9/16] max-w-xs' : 'aspect-square max-w-md'} bg-white rounded-lg overflow-hidden border border-gray-200 mx-auto cursor-grab active:cursor-grabbing`}
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
              
              {/* Caption Editor - Hidden for Instagram Stories */}
              {selectedContentType?.id !== 'instagram-story' && (
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
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-center">
              <div>
                <div className="mx-auto h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center">
                  <span className="text-2xl">{selectedContentType?.icon as any}</span>
                </div>
                <h3 className="mt-4 text-lg font-medium text-gray-900">
                  {chatFlow === 'subject' && (selectedContentType?.id === 'instagram-story' ? 'What story would you like to tell?' : 'What subject would you like to focus on?')}
                  {chatFlow === 'agent' && 'Choose an AI agent for photo selection'}
                  {chatFlow === 'photos' && (selectedContentType?.id === 'instagram-story' ? 'How many photos for your story?' : 'How many photos would you like?')}
                  {chatFlow === 'generating' && (selectedContentType?.id === 'instagram-story' ? 'Creating your story sequence...' : 'Selecting photos with AI...')}
                  {!['subject', 'agent', 'photos', 'generating'].includes(chatFlow) && `Ready to create ${selectedContentType?.name}`}
                </h3>
                <p className="mt-2 text-gray-500">
                  {chatFlow === 'subject' && (selectedContentType?.id === 'instagram-story' ? 'Enter a theme or story concept (e.g., "morning routine", "travel adventure", "food journey", etc.)' : 'Enter a theme or subject for your content (e.g., nature, food, travel, etc.)')}
                  {chatFlow === 'agent' && 'Select an AI agent that matches your content style'}
                  {chatFlow === 'photos' && (selectedContentType?.id === 'instagram-story' ? 'Choose how many photos for your story (3-7 recommended for best narrative flow)' : 'Choose how many photos to select (1-10)')}
                  {chatFlow === 'generating' && (selectedContentType?.id === 'instagram-story' ? 'Please wait while we create your story sequence...' : 'Please wait while we select the best photos for you...')}
                  {!['subject', 'agent', 'photos', 'generating'].includes(chatFlow) && `Chat with the AI to generate content for your ${selectedContentType?.name.toLowerCase()}`}
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

            {/* Agent Selection UI */}
            {chatFlow === 'agent' && availableAgents.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-600">Choose AI agents (click to select multiple):</p>
                  {selectedAgents.length > 0 && (
                    <span className="text-xs text-purple-600 font-medium">
                      {selectedAgents.length} selected
                    </span>
                  )}
                </div>
                <div className="flex space-x-3 overflow-x-auto pb-2">
                  {availableAgents.map((agent) => {
                    const isSelected = selectedAgents.some(a => a.name === agent.name);
                    return (
                      <button
                        key={agent.name}
                        onClick={() => handleAgentClick(agent)}
                        className={`flex-shrink-0 w-32 p-3 border rounded-lg transition-colors text-center cursor-pointer ${
                          isSelected 
                            ? 'bg-purple-100 border-purple-300' 
                            : 'bg-white border-gray-200 hover:border-purple-300 hover:bg-purple-50'
                        }`}
                      >
                        <div className={`w-12 h-12 mx-auto mb-2 rounded-full flex items-center justify-center ${
                          isSelected 
                            ? 'bg-gradient-to-br from-purple-500 to-purple-600' 
                            : 'bg-gradient-to-br from-purple-100 to-purple-200'
                        }`}>
                          <span className={`text-lg font-bold ${
                            isSelected ? 'text-white' : 'text-purple-600'
                          }`}>
                            {agent.name.replace('.md', '').charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className={`font-medium text-sm mb-1 ${
                          isSelected ? 'text-purple-900' : 'text-gray-900'
                        }`}>
                          {agent.name.replace('.md', '')}
                        </div>
                        <div className="text-xs text-gray-600 overflow-hidden" style={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical'
                        }}>
                          {agent.description}
                        </div>
                        {isSelected && (
                          <div className="mt-1 text-xs text-purple-600 font-medium">
                            ✓ Selected
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
                {selectedAgents.length > 0 && (
                  <div className="flex justify-center">
                    <button
                      onClick={handleContinue}
                      className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors text-sm font-medium hover:cursor-pointer"
                    >
                      Continue with {selectedAgents.length} agent{selectedAgents.length > 1 ? 's' : ''}
                    </button>
                  </div>
                )}
                <div className="text-center">
                  <p className="text-xs text-gray-500">
                    Click agents to select/deselect, then click Continue
                  </p>
                </div>
              </div>
            )}
            
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
                placeholder={
                  chatFlow === 'subject' 
                    ? (selectedContentType?.id === 'instagram-story' ? 'Enter your story concept...' : 'Enter the subject or theme...')
                    : chatFlow === 'agent'
                    ? 'Type "continue" when ready...'
                    : chatFlow === 'photos'
                    ? (selectedContentType?.id === 'instagram-story' ? 'Enter number of photos (3-7 recommended)...' : 'Enter number of photos (1-10)...')
                    : 'Describe the content you want to generate...'
                }
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-sm text-gray-900 placeholder-gray-500"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isGenerating}
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

            