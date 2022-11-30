Very simple galvo scan control <br>
Used at the CSHL 2022 Imaging Course for homebrew confocals

To create the environment, install anaconda python distribution https://www.anaconda.com/products/distribution <br> 
And from the folder for this repository run: conda create env -f requirements.yml 

Run the gui.py for the user interface <br>
wavegenbase.py contains a class that handles NI tasks and waveform generation

The codebase is split into two parts, gui.py contains a PyQt gui, and wavegenbase.py contains a class to handle interactions with the NI board (without any GUI elements). <br>
The AI task triggers off the AO task starting, and uses stream_readers/writers with callbacks, which in my experience could handle pretty good data rates with 6#00 series USB boards. 

Wiring: 
AO0 fast axis (x)  
AO1 slow axis (y)  
AI0 photodiode / PMT  

