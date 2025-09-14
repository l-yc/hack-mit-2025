export interface Asset {
  id: number;
  name: string;
  url: string;
  type: string;
  size: number;
  tags: string[];
  metadata: {
    location?: string;
    people?: string[];
    subjects?: string[];
    colors?: string[];
    mood?: string;
    width?: number;
    height?: number;
    duration?: number;
  };
  created_at?: string;
  updated_at?: string;
}
