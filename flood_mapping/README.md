# Climate Modeling for HotspotStoplight

## Repo Overview
This repo contains the code for the climate modeling for HotspotStoplight. The code is written in Python and relies primarily on Google Earth Engine via the `geemap` package. Dependencies are managed by `Poetry` and installation instructions are in the `SETUP.md` file. 

## Flood Modeling
Flood modeling is the first module that we are working for HotspotStoplight. The code is organized in the `data` folder. Data are stored in the `/inputs` and `/outputs` subdirectories, while the `/src` folder contains an ETL pipeline to process Earth Engine data, train a random forest model, and apply the model to predict flood risk for a given area (in this first use case, for Costa Rica).

## Attribution
The Sentinel-1 workflow was adapted from UN-Spider via: https://www.un-spider.org/advisory-support/recommended-practices/recommended-practice-google-earth-engine-flood-mapping/step-by-step

Code to import geoboundaries via python was adapted from `pygeoboundaries`: https://github.com/ibhalin/pygeoboundaries?tab=readme-ov-file

### Research
This project is based on two primary research papers:

Xinxiang Lei, Wei Chen, Mahdi Panahi, Fatemeh Falah, Omid Rahmati, Evelyn Uuemaa, Zahra Kalantari, Carla Sofia Santos Ferreira, Fatemeh Rezaie, John P. Tiefenbacher, Saro Lee, Huiyuan Bian, Urban flood modeling using deep-learning approaches in Seoul, South Korea, Journal of Hydrology, Volume 601, 2021, 126684, ISSN 0022-1694, https://doi.org/10.1016/j.jhydrol.2021.126684.

Kalantar, Bahareh, Naonori Ueda, Vahideh Saeidi, Saeid Janizadeh, Fariborz Shabani, Kourosh Ahmadi, and Farzin Shabani. 2021. "Deep Neural Network Utilizing Remote Sensing Datasets for Flood Hazard Susceptibility Mapping in Brisbane, Australia" Remote Sensing 13, no. 13: 2638. https://doi.org/10.3390/rs13132638 

### Validation

We have cross-referenced (although not formally validated) our results against several data sources, including:

1) This map of flood risk zones across the European Union: https://discomap.eea.europa.eu/floodsviewer/
2) This map of flood risk zones across Nicaragua: https://servidormapas.ineter.gob.ni/mapstore/#/viewer/openlayers/57
3) This global 250m resolution floodplains map: https://gee-community-catalog.org/projects/gfplain250/


# Writeup

## Introduction

- Part of a broader project to get climate hazards data at 30m resolution (give or take) for San Jose, Costa Rica

## Methods

- Assemble conditioning factors based on several research papers + data availability
- Derive pixel labels for known flood events from Sentinel-1 SAR data using an official UN-Spider workflow outlined by ESA.
- Train, test, and validate a random forest model on a stratified sample of 100,000 pixels from all known flood events for a given country
- Create a probability raster to predict flooding likelihood for an entire country's area based on our model
- Validate against several other high-resolution known models + maps

## Results
Find an accuracy ranging from 77% to 97%, with a true positive rate of between 77% and 99%, and a false positive rate from 0.6% to 20%.

## Discussion
Model is good! Needs some fine-tuning for sure but has a lot of potential to advance things. Validation is super important. Better historic training data would be good--deriving things from SAR is 1) already a model and 2) limited to dates from 2014 onwards (and sometimes later in some countries). Also not a perfectly representative sampling of knowing flood events.

## Conclusions

## References