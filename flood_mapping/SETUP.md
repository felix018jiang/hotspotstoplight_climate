# Setup Guide for Flood Mapping Repository

Follow these steps to set up the project environment:

## 1. Install pipx
Follow the instructions at https://github.com/pypa/pipx to install pipx.

## 2. Install pyenv
Follow the instructions at https://github.com/pyenv/pyenv to install pyenv.

## 3. Install Poetry
Visit https://python-poetry.org/docs/ for instructions on installing Poetry.

## 4. Clone the GitHub Repository
Clone the git repository to your local machine by running the following command in your command line interface (CLI):

`git clone https://github.com/HotspotStoplight/Climate`

## 5. Install a local copy of Python
For this project, you'll need Python 3.9. Navigate to `/Climate/flood_mapping` and run `pyenv install 3.9.1`. You may need to set the local version of Python by also running `pyenv local 3.9.1`.

## 6. Install Dependencies with Poetry
In your command line interface (CLI), navigate to the flood_mapping subdirectory with `cd Climate/flood_mapping` and then run `poetry install`.


## 7. Configure Poetry Virtual Environment
Execute the following to create a virtual environment in the project directory:

`poetry config virtualenvs.in-project true`

## 8. Activate the Virtual Environment
Activate the virtual environment by running:

`poetry shell`

If using VS Code, you might need to specify the path to the virtual environment. Run the following command to get the path:

`poetry env info --path`

Copy the output path and paste it into VS Code's Python interpreter path setting. You should now be ready to run the scripts in VS Code.

## Setting User Credentials for Google Cloud

### Install and Initialize gcloud CLI

Follow the instructions to [install the gcloud CLI](https://cloud.google.com/sdk/docs/install). Once the CLI is open, it will ask you to log in. Do so with the appropriate account and pick the relevant cloud project (currently `hotspotstoplight`). Your authentication should automatically be saved to your local machine.

Then run `gcloud auth application-default login` to authenticate.

## Running the Flood Prediction Script
To run the flood prediction script, you'll need:
1) An AOI (area of interest) in the form of a GeoJSON file saved in the `data/inputs` directory.
2) A set of known flood dates in the form of a CSV file saved in the `data/inputs` directory.

To run the script, navigate to the `flood_mapping` directory and activate the virtual environment with `poetry shell`. Then, run the main script with `python .\data\src\script.py`. This should generate a flood prediction map in the `data/outputs` bucket in Google Cloud.