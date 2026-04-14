# Create PIM (Platform Independent Model)

In this part, you will learn how to transform a generated PSM instance into a PIM instance using the MiSAR QVT transformation.

## Open Transformation
Right click:
MisarTransformation3.qvto → Run As → Run Configurations

<center><img src="/assets/images/pim/pim-run.png" alt="Missing dependencies" width="600"/></center>


## Select Transformation
Choose:
QVT Operational Transformation

<center><img src="/assets/images/pim/pim-transform.png" alt="Missing dependencies" width="600"/></center>

## Configure Input/Output

### Input (PSM)
Select generated PSM file (.xmi)

### Output (PIM)
Choose output location and filename

<center><img src="/assets/images/pim/pim-select-psm-and-pim.png" alt="Missing dependencies" width="600"/></center>

## Run Transformation
Click Run

## View Output
Right click generated file → Open With → Sample Reflective Ecore Model Editor

<center><img src="/assets/images/pim/pim-show-as.png" alt="Missing dependencies" width="600"/></center>

## Result
You will see:
- Microservices
- Functional vs Infrastructure services
- Dependencies

<center><img src="/assets/images/pim/pim-success-example.png" alt="Missing dependencies" width="600"/></center>