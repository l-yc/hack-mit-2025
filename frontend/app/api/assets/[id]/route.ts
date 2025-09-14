import { NextRequest, NextResponse } from 'next/server';
import { updateAssetTags, deleteAsset } from '@/lib/db-direct';

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { tags } = await request.json();
    const assetId = parseInt(params.id);

    if (isNaN(assetId)) {
      return NextResponse.json({ error: 'Invalid asset ID' }, { status: 400 });
    }

    const updatedAsset = await updateAssetTags(assetId, tags);
    return NextResponse.json({ asset: updatedAsset });
  } catch (error) {
    console.error('Error updating asset tags:', error);
    return NextResponse.json({ error: 'Failed to update asset tags' }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const assetId = parseInt(params.id);

    if (isNaN(assetId)) {
      return NextResponse.json({ error: 'Invalid asset ID' }, { status: 400 });
    }

    await deleteAsset(assetId);
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting asset:', error);
    return NextResponse.json({ error: 'Failed to delete asset' }, { status: 500 });
  }
}
