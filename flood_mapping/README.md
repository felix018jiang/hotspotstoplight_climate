# Climate Modeling for HotspotStoplight

## Repo Overview
This repo contains the code for the climate modeling for HotspotStoplight. The code is written in Python and relies primarily on Google Earth Engine via the `geemap` package. Dependencies are managed by `Poetry` and installation instructions are in the `SETUP.md` file. 

## Flood Modeling
Flood modeling is the first module that we are working for HotspotStoplight. The code is organized in the `data` folder. Data are stored in the `/inputs` and `/outputs` subdirectories, while the `/src` folder contains an ETL pipeline to process Earth Engine data, train a random forest model, and apply the model to predict flood risk for a given area (in this first use case, for Costa Rica).