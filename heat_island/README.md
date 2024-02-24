# Overview

## Relevant research

https://www.sciencedirect.com/science/article/pii/S2667010021001712

https://google-earth-engine.com/Human-Applications/Heat-Islands/

https://appliedsciences.nasa.gov/sites/default/files/2020-11/UHI_Part1_v5.pdf

https://medium.com/@ridhomuh002/analyzing-land-surface-temperature-lst-with-landsat-8-data-in-google-earth-engine-f4dd7ca28e70

https://developers.google.com/earth-engine/datasets/catalog/JAXA_GCOM-C_L3_LAND_LST_V1

https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2#description

For downscaling these data: https://www.mdpi.com/2072-4292/14/16/4076

For prediction: https://www.mdpi.com/1660-4601/20/3/2642

https://isprs-archives.copernicus.org/articles/XLII-4-W18/1123/2019/isprs-archives-XLII-4-W18-1123-2019.html

https://link.springer.com/article/10.1007/s40808-023-01822-2

https://www.mdpi.com/2225-1154/7/1/5

https://www.mdpi.com/2072-4292/12/9/1471?ref=https://coder.social

## Necessary data:

elevation?
dist to equator?
dist to coast?
land cover
ndvi
nbdi
emissivity?
LST (dependent variable)

Adding longitute and latitude to the data as training features:
```
image = ee.Image('your/image/collection')
withLatLon = image.addBands(ee.Image.pixelLonLat())
```

## Limitations
Predicting changes in building volume and individual tree cover is not possible and therefore limits the granularity of the model