// Configuration for asset service backend
export const config = {
  // Switch between 'flask' and 'prisma' backends
  assetServiceType: 'flask' as 'flask' | 'prisma',
  
  // Flask backend configuration
  flaskBackendUrl: process.env.NEXT_PUBLIC_FLASK_BACKEND_URL || 'http://18.217.7.13:6741',
  
  // Feature flags
  features: {
    enableTagging: true,
    enableSearch: true,
    enableAssetDeletion: true,
  }
};

export default config;
