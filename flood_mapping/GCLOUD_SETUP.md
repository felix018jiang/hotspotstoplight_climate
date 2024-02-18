# Setting up our Virtual Machine (VM) on Google Cloud
This guide will walk you through the process of setting up a new VM on Google Cloud, connecting to it via SSH, and installing necessary software.

## Step 1: Create a new VM with appropriate scopes
First, we need to create a new VM. We'll use the gcloud command-line tool to do this. The following command creates a new VM named climate in the us-east4-b zone, with a machine type of n2-standard-8. We're also specifying a service account and setting the scope to cloud-platform.

```
gcloud compute instances create climate --zone=us-east4-b --machine-type=n2-standard-8 --service-account=636254137257-compute@developer.gserviceaccount.com --scopes=https://www.googleapis.com/auth/cloud-platform
```

## Step 2: Connect to the VM via SSH
Next, we'll connect to the VM using SSH. The following command connects to the climate VM in the us-east4-b zone.

```
gcloud compute ssh climate --zone=us-east4-b
```

## Step 3: Install Python
Once connected, we'll update the package lists for upgrades and new packages, and then install Python and pip.

```
sudo apt-get update && sudo apt-get install python3-pip -y
```

## Step 4: Install Git
We'll also need Git for version control. Install it with the following command:

```
sudo apt-get install -y git
```

## Step 5: Install pipx, pyenv, and poetry
Next, we'll install several Python tools: pipx, pyenv, and poetry. These tools help manage Python versions and packages.

First, we'll install pipx, a tool to install and run Python applications in isolated environments.

```
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip

python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Next, we'll install pyenv, a tool to manage multiple Python versions.

```
sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
xz-utils tk-dev libffi-dev liblzma-dev python-openssl git
curl https://pyenv.run | bash

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"

exec "$SHELL"
```

Finally, we'll install poetry, a tool for dependency management and packaging in Python.

```
pipx install poetry
```

## Step 6: Install oh-my-zsh
Oh-my-zsh is a community-driven framework for managing your Zsh configuration. It comes bundled with a ton of helpful functions, helpers, plugins, and themes.

(This step is optional. If you prefer to use the default bash shell, you can skip this step.)

```
sudo apt-get install zsh -y
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

## Step 7: Create an SSH key for GitHub
Next, we'll create an SSH key that we can use with GitHub. When prompted, press enter to accept the default file location and passphrase.

```
ssh-keygen -t rsa -b 4096 -C "
```

Then, output the public key and copy it:

```
cat ~/.ssh/id_rsa.pub
```

Add the public key to your GitHub account's SSH keys in the settings.

Finally, you can clone the Git repository you want to work with.

```
git clone git@github.com:HotspotStoplight/Climate.git
```

That's it! You've successfully set up a new VM on Google Cloud and installed the necessary software. You're now ready to start working on your project.

## Step 8: Navigate to the project directory and run script.py
To run the flood modeling script, run the following code to navigate to the project directory and execute the script.

```
cd Climate/flood_modeling
poetry shell
python3 data/src/script.py
```