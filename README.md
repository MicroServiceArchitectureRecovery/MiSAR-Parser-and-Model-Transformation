# MiSAR Parser, Transformation Engine and AIO

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Java](https://img.shields.io/badge/Java-OpenJDK%2021-ED8B00?logo=openjdk&logoColor=white)](https://openjdk.org/)
[![Eclipse](https://img.shields.io/badge/Eclipse-QVTo-2C2255?logo=eclipseide&logoColor=white)](https://www.eclipse.org/)
[![Documentation](https://img.shields.io/badge/documentation-MiSAR-2563eb?logo=readthedocs&logoColor=white)](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/)
[![Parser Tests](https://img.shields.io/github/actions/workflow/status/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation/parser-tests.yml?label=tests)](https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation/actions)
[![Doc Deployment](https://img.shields.io/github/actions/workflow/status/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation/deploy-docs.yml?label=docs)](https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation/actions)

This repository contains the operational core of **MiSAR**: the All-in-One launcher, the source-code parser, the Platform Specific Model generation workflow, and the resources used to transform a PSM into a Platform Independent Model.

The parser analyses implementation artefacts from a microservice system and recovers a **Platform Specific Model (PSM)**. The transformation stage then derives a **Platform Independent Model (PIM)**, which represents the recovered architecture at a higher level of abstraction.

## Repository role

```mermaid
flowchart LR
    A[Source code and configuration] --> B[MiSAR Parser]
    B --> C[PSM]
    C --> D[QVTo Transformation]
    D --> E[PIM]
    E --> F[MiSAR Graphical Model Generator]
```

This repository provides:

- the **MiSAR All-in-One launcher** (`MiSAR.py`);
- the **MiSAR Parser** and language-specific analysis logic;
- PSM generation and validation;
- transformation metamodels and QVTo resources;
- the maintained MiSAR documentation source;
- automated tests and supporting release configuration.

## Documentation

Begin with the maintained documentation:

- **[MiSAR documentation](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/)**
- **[Installation](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/installation/)**
- **[Create a PSM](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/create-psm/)**
- **[QVT installation and setup](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/qvt-manual-installation/)**
- **[Create a PIM](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/create-pim/)**
- **[Changelog](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/changelog/)**

## Copyright

© 2020-2026 Dr Nour Ali, Brunel University London. All rights reserved. MiSAR is made openly available for research and evaluation purposes. The intellectual property and copyright of this tool and its associated research remain with Dr Nour Ali and Brunel University London.