# MiSAR – Microservice Architecture Recovery Toolset

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


## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation
```

### 2. Run MiSAR

```bash
python MiSAR.py
```

On first launch:

-   Dependencies are installed automatically
-   Confirmation message is shown upon success

### 3. Generate a PSM

-   Launch the parser
    
-   Select project root and Docker Compose
    
-   Use automatic importer
    
-   Generate `.xmi` model
    

👉 Full guide:  
`docs/create-psm.md`

----------

### 4. Transform PSM → PIM

-   Open Eclipse Modeling Tools
    
-   Configure QVT mappings
    
-   Run transformation
    

👉 Full guide:  
`docs/create-pim.md`

----------

## 📚 Documentation

Documentation has been migrated to a structured MkDocs-based system:

-   Installation → `docs/installation.md`
    
-   QVT Setup → `docs/qvt-setup.md`
    
-   Create PSM → `docs/create-psm.md`
    
-   Create PIM → `docs/create-pim.md`
    
-   Graphical Generator → `docs/graphical-generator.md`
    

----------

## 🧪 Example Systems

MiSAR has been evaluated on:

-   MicroCompany
    
-   TrainTicket
    
-   MusicStore
    

## 🛠️ Recent Improvements

-   Cross-platform file handling using `pathlib`
-   Improved PSM generation feedback
-   Documentation migrated from static PDFs to MkDocs
-   Automatic importer stability improvements
    

👉 Full history: `docs/changelog.md`

## ⚠️ Notes

-   Parser is currently focused on **Java-based microservices**
-   QVT setup requires Eclipse Modeling Tools
-   Some legacy installation behaviours (auto-download) are under review

## 🤝 Contributing

Contributions are welcome:

1.  Create a feature branch
    
2.  Submit a pull request
    
3.  Provide clear reproduction steps

## 👨‍💻 Authors

-   Dr Nour Ali – Project Lead 
-   Contributors – Research Assistants and Students


## 🔗 Links

-   Main Repository: [https://github.com/MicroServiceArchitectureRecovery/misar](https://github.com/MicroServiceArchitectureRecovery/misar)
-   Parser & Transformation: [https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation](https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation)