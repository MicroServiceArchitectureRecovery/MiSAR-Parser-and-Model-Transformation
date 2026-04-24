# Graphical Model Generator

This is the final step in the MiSAR process, where the recovered PIM is transformed into visual representations (UML diagrams) and summaries.

## Overview
This step is optional and generates UML diagrams.

## Launch Graphical Model Generator
Run `python3 MiSAR.py` to open MiSAR AIO, then click **Launch**

![MiSAR AIO](assets/images/aio/misar-aio.png){ width="500" }

![Graphical generator](assets/images/misar-jar/misar-jar.png)

## Input
Provide the PIM file generated from the transformation step.

> If you don't have a PIM file, you can simply change the file extension of the generated PIM file from `.xmi` to `.PIM` (case-sensitive) and use that as input.

## Outputs
- UML diagrams

![Dependency view](assets/images/misar-jar/micro-company-dependency-view.png)

- Excel summaries

![Excel example](assets/images/misar-jar/micro-company-xls-example.png)

- Architecture overview

## Notes
- Useful for visualising system structure
- Helps in analysis and reporting