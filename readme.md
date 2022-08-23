Very simple galvo scan control 
Used at the CSHL 2022 Imaging Course for homebrew confocals

To create the environment, install anaconda python distribution https://www.anaconda.com/products/distribution 
And then run: conda create env -f requirements.yml 

Run the gui.py for the user interface
wavegenbase.py contains a class that handles NI tasks and waveform generation

Wiring: 
AO0 fast axis (x)
AO1 slow axis (y)
AI0 photodiode 
