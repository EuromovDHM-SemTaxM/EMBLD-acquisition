# EMBLD Acquisition Dashboard

This repository contains the software necessary for driving the acquisition of the EMBLD dataset. If this acquistion programme is running on the same machine as QTM for MoCAP or Oxysoft for fNIRS, you must run it on windows as these acquistion platroforms are windows only. 
If you are running on a separate machine than the one used for acquistion, please make sure you are on the same local network so that the communication protocols can operate. 

# Installation
First, please install all dependencies listed in `requirements.txt` with `pip install -r requirements.txt`, then you also need to install the mpg123 programme to play the audio instructions. 

## On Linux
Please use you package manager, mpg123 is a very standard tool to play mp3 sound files. 
On debian-based distributions: `sudo apt-get install mpg123`
On fedora based distributions: `sudo yum install mpg123`

## On MacOSX 
It is recommended that you use the homebrew (https://docs.brew.sh/Installation) package manager. After installing homebrew:

`sudo brew install mpg123`

## On Windows
It is recommended to use the Chocolatey package manager (https://chocolatey.org/install). After installing Chocolatey, please run, in a PowerShell with administrative priviledges:
`choco install mpg123`

# Action specification syntax 
The list of elementary or composed actions can be defined very flexibly through the config.json file, this section comprehensively document the possibilities offered by this mechanim. 

