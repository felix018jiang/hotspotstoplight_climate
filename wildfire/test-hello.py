import ee
import geemap
# Trigger the authentication flow.
ee.Authenticate()

# Initialize the library.
ee.Initialize(project='musa-wildfire-449918')

print("hello world")

dataset = (
    ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE')
      .filter(ee.Filter.date('2020-01-01', '2021-01-01'))
)


maximumDrought = dataset.select('pdsi').mean()

# Define visualization parameters for the temperature image
maximumDroughtVis = {
    'min': -10,
    'max': 10,
    'palette': [
        '#8b0000',  # Extreme drought (dark red)
        '#d73027',  # Severe drought (red)
        '#fc8d59',  # Moderate drought (orange)
        '#fee08b',  # Mild drought (yellow)
        '#f0f0f0',  # Near normal (white)
        '#d9ef8b',  # Moderately wet (light green)
        '#91cf60',  # Very wet (green)
        '#4575b4',  # Extremely wet (blue)
        '#313695'   # Deep blue (most wet)
    ]
}

Map = geemap.Map()
Map.setCenter(-51.9253, -14.2350, 3)
Map.addLayer(maximumDrought, maximumDroughtVis, 'Maximum Drought')
Map.to_html('mapTest.html')