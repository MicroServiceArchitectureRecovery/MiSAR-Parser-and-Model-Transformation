# MiSAR – Microservice Architecture Recovery Toolset

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Java](https://img.shields.io/badge/Java-OpenJDK%2021-orange)
![Eclipse](https://img.shields.io/badge/Eclipse-2024-purple)
![QVTo](https://img.shields.io/badge/QVTo-3.11.2-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

[![MiSAR Manual](https://img.shields.io/badge/Read%20the%20Manual-docs%2Findex.md-blue)](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/)
[![YouTube Demo](https://img.shields.io/badge/Watch%20the%20Demo-YouTube-red)](https://www.youtube.com/watch?v=sdRDkLesyS0)
[![GitHub stars](https://img.shields.io/github/stars/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation?style=social)](https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation/stargazers)

MiSAR is a research-driven toolset designed to semi-automatically recover architectural models from implemented microservice-based systems using a Model-Driven Architecture (MDA) approach.


## Overview

MiSAR transforms implementation artefacts into architectural models through the following pipeline:


```sh

Code → PSM → PIM → UML

```

- **PSM (Platform Specific Model)** → extracted from source code and configuration  
- **PIM (Platform Independent Model)** → abstract representation of the architecture  
- **UML / Visualisation** → optional diagrams and summaries  

A full demonstration is available here:  
👉 [https://www.youtube.com/watch?v=sdRDkLesyS0](https://www.youtube.com/watch?v=sdRDkLesyS0)

## Supported Technologies/Frameworks
- Java (Spring Boot / Spring Cloud)
- Docker / docker-compose
- Python (Flask / FastAPI / Django)

##  Core Components

### 1. MiSAR Parser
- Analyses microservice-based systems  
- Supports:
  - Java (Spring Boot / Spring Cloud)
  - Docker / docker-compose
  - XML / YAML (e.g. `pom.xml`)  

👉 Output: **PSM (.xmi)**

### 2. Transformation Engine (QVT)
- Converts PSM → PIM  
- Uses QVT Operational (QVTo) inside Eclipse  

👉 Output: **PIM (.xmi)**

### 3. Graphical Model Generator
- Generates:
  - UML diagrams  
  - Excel summaries  
  - dependency views  

👉 Final architecture visualisation

## 📚 Documentation

[Full Documentation](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/)

[Installation instructions](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/installation)

[Recent Improvements](https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/changelog)

## 🧪 Example Systems

MiSAR has been evaluated on:

-   [MicroCompany](https://github.com/idugalic/micro-company)
    
-   [TrainTicket](https://github.com/jo102tz/train-ticket)
    
-   [MusicStore](https://github.com/SteeltoeOSS/Samples/tree/main/MusicStore)


👉 Full history: `docs/changelog.md`

## ⚠️ Notes

-   Parser is currently focused on **Java-based microservices**
-   QVT setup requires Eclipse Modeling Tools
-  MISAR only requires internet access during the initial setup to download necessary dependencies. Once set up, it can be used offline without any issues.

## 🤝 Contributing

Contributions are welcome:

1.  Create a feature branch
    
2.  Submit a pull request
    
3.  Provide clear reproduction steps

## 👨‍💻 Authors

© 2020-2026 Dr Nour Ali, Brunel University London. All rights reserved.
MiSAR is made openly available for research and evaluation purposes. The intellectual property and copyright of this tool and its associated research remain with Dr Nour Ali and Brunel University London. If you use MiSAR in your work, please cite the relevant publications.
-   Contributors – Nuha Alshuqayran and students


## 🔗 Links

-   Main Repository: [https://github.com/MicroServiceArchitectureRecovery/misar](https://github.com/MicroServiceArchitectureRecovery/misar)
-   Parser & Transformation: [https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation](https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation)
