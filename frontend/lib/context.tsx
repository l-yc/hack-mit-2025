'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Asset } from '@/types/asset';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  assets?: Asset[];
}

interface ContentType {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  dimensions: string;
}

interface AppContextType {
  // Assets state
  assets: Asset[];
  setAssets: (assets: Asset[]) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  selectedTags: string[];
  setSelectedTags: (tags: string[]) => void;
  
  // Generate state
  selectedContentType: ContentType | null;
  setSelectedContentType: (type: ContentType | null) => void;
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  chatFlow: string;
  setChatFlow: (flow: string) => void;
  selectedAssets: Asset[];
  setSelectedAssets: (assets: Asset[]) => void;
  postCaption: string;
  setPostCaption: (caption: string) => void;
  userPurpose: string;
  setUserPurpose: (purpose: string) => void;
  userTarget: string;
  setUserTarget: (target: string) => void;
  selectedProject: string;
  setSelectedProject: (project: string) => void;
  currentImageIndex: number;
  setCurrentImageIndex: (index: number) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  // Assets state
  const [assets, setAssets] = useState<Asset[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  
  // Generate state
  const [selectedContentType, setSelectedContentType] = useState<ContentType | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatFlow, setChatFlow] = useState('purpose');
  const [selectedAssets, setSelectedAssets] = useState<Asset[]>([]);
  const [postCaption, setPostCaption] = useState('');
  const [userPurpose, setUserPurpose] = useState('');
  const [userTarget, setUserTarget] = useState('');
  const [selectedProject, setSelectedProject] = useState('');
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  return (
    <AppContext.Provider value={{
      assets,
      setAssets,
      searchQuery,
      setSearchQuery,
      selectedTags,
      setSelectedTags,
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
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}
