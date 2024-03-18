# Applies scaling factors.
def apply_scale_factors(image):
    # Scale and offset values for optical bands
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    
    # Scale and offset values for thermal bands
    thermal_bands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    
    # Add scaled bands to the original image
    return image.addBands(optical_bands, None, True).addBands(thermal_bands, None, True)