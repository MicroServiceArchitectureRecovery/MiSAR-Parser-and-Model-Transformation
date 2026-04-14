# QVT Setup (Eclipse)

> This guide is for setting up the QVT transformation engine in Eclipse. It is not required to run the MiSAR parser or generate PSM files, but it is necessary for transforming PSM to PIM.
> 
> The QVT transformation engine is used to transform the generated PSM into a PIM, which is the recovered architectural model of the microservice system.
>

## Install Eclipse Modeling Tools
Download Eclipse Modeling Tools package. Latest version can be found at: [https://www.eclipse.org/downloads/packages/](https://www.eclipse.org/downloads/packages/)

## Import Project
File → Open Projects from File System

<center><img src="/assets/images/qvt/qvt-select.png" alt="Missing dependencies" width="200"/></center>

Select:
TransformationEngineNecessities folder

<center><img src="/assets/images/qvt/qvt-pick.png" alt="Missing dependencies"/></center>

## Configure Metamodels
Go to:
Project → Properties → QVT Settings → Metamodel Mappings

<center><img src="/assets/images/qvt/qvt-mapping.png" alt="Missing dependencies" width="200"/></center>
<center><img src="/assets/images/qvt/qvt-mapping-setup.png" alt="Missing dependencies"/></center>

Add:

### PIM
| Source                         | Target                           |
|--------------------------------|----------------------------------|
| http://localhost/mdd/PIM.ecore | platform:/resource/.../PIM.ecore |

<center><img src="/assets/images/qvt/qvt-mapping-pim.png" alt="Missing dependencies" width="600"/></center>

### PSM
| Source                         | Target                           |
|--------------------------------|----------------------------------|
| http://localhost/mdd/PSM.ecore | platform:/resource/.../PSM.ecore |

<center><img src="/assets/images/qvt/qvt-mapping-psm.png" alt="Missing dependencies" width="600"/></center>


## Notes
- QVT is already included in Eclipse Modelling Tools (2024-06+ until 2025-09)
- No marketplace installation required
