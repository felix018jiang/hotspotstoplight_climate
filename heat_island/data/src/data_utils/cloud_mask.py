# Function to Mask Clouds and Cloud Shadows in Landsat 8 Imagery
def cloud_mask(image):
    # Define cloud shadow and cloud bitmasks (Bits 3 and 5)
    cloud_shadow_bitmask = 1 << 3
    cloud_bitmask = 1 << 5
        
    # Select the Quality Assessment (QA) band for pixel quality information
    qa = image.select('QA_PIXEL')
        
    # Create a binary mask to identify clear conditions (both cloud and cloud shadow bits set to 0)
    mask = qa.bitwiseAnd(cloud_shadow_bitmask).eq(0).And(qa.bitwiseAnd(cloud_bitmask).eq(0))
        
    # Update the original image, masking out cloud and cloud shadow-affected pixels
    return image.updateMask(mask)