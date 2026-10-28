@echo off

beebasm -i criticalmass.6502 -do criticalmass.ssd -v -opt 2 -title CRITICALMASS > list.txt
if ERRORLEVEL 1 exit /B

beebjit -rom B roms/DDoc1.09.rom -0 criticalmass.ssd -writeable -mutable -autoboot
