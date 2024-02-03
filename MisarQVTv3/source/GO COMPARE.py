import filecmp
import os
import datetime

x = True

while x == True:
    f1 = "C:/Users/Student/MisAR/MisarQVTv3/source/woggies-PSM.xmi"
    f2 = "C:/Users/Student/MisAR/MisarQVTv3/source/artifactsWoggies.xmi"

    print("Are the old and new results the same?")
    print(filecmp.cmp(f1, f2))

    input("Press Enter to compare the two files again...")
