# --- HOW TO USE FOR DUMMIES ---    
 Step 1: Betaflight Blackbox Explorer / Configurator: Select your log and export as CSV    
 Step 2: Dump them in the same folder as this file. Right click "Raw" and "Save As" to download to your pc. You can edit .py files with notepad    
 Step 3: Install python 3 if you haven't done so yet    
 Step 4: `pip install scipy` etc. as needed in cmd prompt, shell, terminal illness or whatevers you got    
 Step 5: `python.exe thisfile.py` or `py thisfile.py`    
 Step 6: Profit?!?    
 Step 7: If it sounds bad, adjust OVERTONE_WEIGHTS and run this file again   
 
 Please note that eRPM reported values isn't the real RPM, there's some scalar involved   
 
 No warranty provided for you bricking your own system out of your own stupidity whatever blah blah   

 ___

 ## Blackbox Requirements:

 - Motor (used for motor strain)
 - RPM (used motor RPM, duh)
 - Gyro (used for stereo/FM/AM modulation effects)
 - Raw Gyro (used for noise)
 - RC Setpoint (used for some stupid noise generation effect but its kinda shitty so I might remove it in the future)

Note: Higher frequency blackbox logging rate will give more accurate sounding motors but you can't record as long. Make sure you clear your blackbox log before flying (to access menu: left stick left, right stick up, and then navigate to features -> blackbox -> scroll down and clear blackbox log)

Don't forget you can use the blackbox logs to overlay HUDs like stick positions and do gyroflow shenanigans!

 ___
 
   DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE    
   Version 2, December 2004    

 Copyright (C) 2004 Sam Hocevar <sam@hocevar.net>    

 Everyone is permitted to copy and distribute verbatim or modified    
 copies of this license document, and changing it is allowed as long    
 as the name is changed.    

   DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE    
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION    

  0. You just DO WHAT THE FUCK YOU WANT TO.    
