# Setup Guide for Flood Mapping Repository

Follow these steps to set up the project environment:

## 1. Install pipx
Follow the instructions at https://github.com/pypa/pipx to install pipx.

## 2. Install Poetry
Visit https://python-poetry.org/docs/ for instructions on installing Poetry.

## 3. Clone the GitHub Repository
Clone the git repository to your local machine by running the following command in your command line interface (CLI):

`git clone https://github.com/HotspotStoplight/Climate`

## 4. Install Dependencies with Poetry

In your command line interface (CLI), navigate to the flood_mapping subdirectory with `cd Climate/flood_mapping` and then run `poetry install`.


## 5. Configure Poetry Virtual Environment
Execute the following to create a virtual environment in the project directory:

`poetry config virtualenvs.in-project true`

## 7. Activate the Virtual Environment
Activate the virtual environment by running:

`poetry shell`

If using VS Code, you might need to specify the path to the virtual environment. Run the following command to get the path:

`poetry env info --path`

Copy the output path and paste it into VS Code's Python interpreter path setting. You should now be ready to run the scripts in VS Code.
