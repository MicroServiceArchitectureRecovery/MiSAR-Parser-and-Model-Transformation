# Changelog

## V2026-07-16

- Updated the MiSAR documentation screenshots for the MiSAR v3 interface.
- Added documentation for the new MiSAR AIO **Options** screen, including display size, automatic/manual update checks, and debug mode.
- Added documentation for Parser session recovery and restoring previously saved paths and inputs.
- Updated the Parser documentation to use the clearer **Microservice Project Folders** wording.
- Documented that shortened paths remain visible in the Parser while copying retrieves the full path.
- Clarified that users may use either Eclipse Modelling Tools or the lighter Eclipse IDE for Java Developers.
- Added EMF SDK installation instructions using the Eclipse 2026-06 update site: `https://download.eclipse.org/releases/2026-06`.
- Added troubleshooting guidance for a missing **Sample Reflective Ecore Model Editor**.

## V2026-05-28

- Added a Mermaid sequence diagram to the welcome page to visually explain the MiSAR workflow from source code to UML output.
- Updated the documentation navigation order so the changelog appears last and the manual follows the expected user workflow.
- Enhanced the Create PSM guide with a clearer step-by-step walkthrough for using the MiSAR Parser.
- Updated the Create PSM field table to match the latest MiSAR Parser GUI numbering and labels.
- Clarified how Docker Compose files are used by the automatic importer.
- Added guidance for manually selecting microservice build directories when automatic detection is incomplete.
- Added notes explaining that non-Java projects may require manual microservice directory selection while improved automatic detection is under development.
- Added guidance for the Maven `pom.xml` prompt during PSM creation.
- Updated the QVT plugin installation and QVT setup documentation with additional instructions and clarifications.
- Enhanced the Create PIM guide with more detailed instructions for running the PSM to PIM transformation.
- Added guidance for using the Graphical Model Generator after generating a PIM.
- Added Next Steps sections to all documentation pages to guide users through the expected MiSAR workflow and link to the next relevant guides.

## V2026-05-19
- Updated the Create PSM documentation to improve clarity around parser input fields.
- Added descriptions for each MiSAR Parser input field, including mandatory and optional fields.
- Improved the Automatic Importer section to explain how Docker Compose files can be used to populate related project fields automatically.
- Changed the Outdated MISAR-AIO picture.

## V2026-05-16
- Added documentation for downloading and installing MiSAR from GitHub, including both ZIP download and Git clone options.
- Added a prerequisites section to the main documentation, listing required and tested versions for Python, Java, Eclipse, QVTo, and Python dependencies.
- Added uninstallation documentation explaining how MiSAR modules can be removed using the AIO uninstall buttons.
- Added guidance for verifying uninstallation by checking the `MiSAR` directory inside the user home directory.
- Updated the documentation navigation order to follow the expected MiSAR user workflow
- Updated the index page section list to match the revised navigation order.

## V2026-04-15
- Introduced MiSAR dynamic manual generation, allowing for real-time updates and improvements to the documentation.
- Introduced a new changelog format to better track updates and changes across the MiSAR project.
- Removed Original MiSAR manual PDF from the repository, as the dynamic manual generation provides a more up-to-date and accessible documentation format.

## V2026-04-13
- Cross-platform file handling was updated to use `pathlib`, improving macOS/Linux compatibility.
- Added a repository `.gitignore` and cleaned local IDE/virtual-environment noise.
- Improved PSM generation feedback and automatic uploader-related file handling.

## V2024-06-28
- Consolidated and renamed manual assets for the 28 June release set.
- Removed obsolete PDFs and outdated integration files from the repository.
- Updated project titles and cleaned up uploaded assets.

## V2024-06-21
- Added the final `MiSAR.py` application entry point.
- Ran updater-focused changes and tests.
- Removed legacy parser and QVT Operational directories.

## V2024-04-08
- Merged the Python parser work from the Girish branch. 
- Added Python AST sample project scaffolding and parser integration updates.

## V2024-02-06
- Expanded the Python parser implementation.
- Added parser ecore/AST support files and sample project assets.

## V2023-12-04
- Added graphical model generator functionality.

## V2023-11-15
- Refreshed the manual assets.
- Increased font sizing for improved readability.

## V2023-11-06
- Updated the GUI and integration flow.
- Simplified PSM import handling and added a manual fallback path.

## V2023-10-30
- Stabilized the MiSAR auto-updater.

## V2023-10-19
- Introduced MiSAR AIO to launch the parser, transformation engine, and graphical model generator.

## V2023-10-16
- Added automatic PSM import handling.
- Supported custom XMI output names and a folder-based project layout.

## V2023-10-05
- Refactored the parser main flow and related GUI hooks.
- Verified the refactor still produced matching `.xmi` output.

## V2023-10-04
- Fixed output-file handling.

## V2023-10-03
- Added the automatic importer.

## V2023-09-29
- Improved performance and completed the object-oriented GUI.

## V2023-09-25
- Added Python analysis support.

## V2020 
- The original MiSAR manual was created in 2020 and has been updated over time. The changelog above reflects the major updates and changes made to the MiSAR project and its documentation since then.
