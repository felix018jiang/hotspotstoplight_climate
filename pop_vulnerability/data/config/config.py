import os
import ee
from google.cloud import storage

cloud_project = 'hotspotstoplight'

ee.Initialize(project=cloud_project)