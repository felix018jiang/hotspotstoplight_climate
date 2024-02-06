# Climate Modeling for HotspotStoplight

## Repo Overview
This repo contains the code for the climate modeling for HotspotStoplight. The code is written in Python and relies primarily on Google Earth Engine via the `geemap` package. Dependencies are managed by `Poetry` and installation instructions are in the `SETUP.md` file. 

## Flood Modeling
Flood modeling is the first module that we are working for HotspotStoplight. The code is organized in the `data` folder. Data are stored in the `/inputs` and `/outputs` subdirectories, while the `/src` folder contains an ETL pipeline to process Earth Engine data, train a random forest model, and apply the model to predict flood risk for a given area (in this first use case, for Costa Rica).

### Research
This project is based on two primary research papers:

Xinxiang Lei, Wei Chen, Mahdi Panahi, Fatemeh Falah, Omid Rahmati, Evelyn Uuemaa, Zahra Kalantari, Carla Sofia Santos Ferreira, Fatemeh Rezaie, John P. Tiefenbacher, Saro Lee, Huiyuan Bian,
Urban flood modeling using deep-learning approaches in Seoul, South Korea,
Journal of Hydrology,
Volume 601,
2021,
126684,
ISSN 0022-1694,
https://doi.org/10.1016/j.jhydrol.2021.126684.
(https://www.sciencedirect.com/science/article/pii/S0022169421007320)
Abstract: Identification of flood-prone sites in urban environments is necessary, but there is insufficient hydraulic information and time series data on surface runoff. To date, several attempts have been made to apply deep-learning models for flood hazard mapping in urban areas. This study evaluated the capability of convolutional neural network (NNETC) and recurrent neural network (NNETR) models for flood hazard mapping. A flood-inundation inventory (including 295 flooded sites) was used as the response variable and 10 flood-affecting factors were considered as the predictor variables. Flooded sites were then spatially randomly split in a 70:30 ratio for building flood models and for validation purposes. The prediction quality of the models was validated using the area under the receiver operating characteristic curve (AUC) and root mean square error (RMSE). The validation results indicated that prediction performance of the NNETC model (AUC = 84%, RMSE = 0.163) was slightly better than that of the NNETR model (AUC = 82%, RMSE = 0.186). Both models indicated that terrain ruggedness index was the most important predictor, followed by slope and elevation. Although the model output had a relative error of up to 20% (based on AUC), this modeling approach could still be used as a reliable and rapid tool to generate a flood hazard map for urban areas, provided that a flood inundation inventory is available.
Keywords: Flood inundation; Cities; GIS; Deep-learning; Predictors

Kalantar, Bahareh, Naonori Ueda, Vahideh Saeidi, Saeid Janizadeh, Fariborz Shabani, Kourosh Ahmadi, and Farzin Shabani. 2021. "Deep Neural Network Utilizing Remote Sensing Datasets for Flood Hazard Susceptibility Mapping in Brisbane, Australia" Remote Sensing 13, no. 13: 2638. https://doi.org/10.3390/rs13132638 