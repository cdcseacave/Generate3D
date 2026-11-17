@echo off
rem Render the rest of the 2K fly-through (frames 950-2220; 1-949 were rendered on the Mac).
rem Existing frames are skipped, so this can be stopped and started again.
cd /d D:\apartment
"D:\Apps\blender\blender.exe" -b out\apartment_packed.blend -P apartment\flythrough.py -- final 950 2220 >> out\fly_final.log 2>&1
