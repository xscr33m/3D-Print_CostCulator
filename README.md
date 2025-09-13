[![Pricing](https://img.shields.io/badge/Price-Free-green?style=for-the-badge&color=green)](https://github.com/xscr33m/3D-Print_CostCulator/)
[![Downloads](https://img.shields.io/github/downloads/xscr33m/3D-Print_CostCulator/total?style=for-the-badge&color=gold)](https://github.com/xscr33m/3D-Print_CostCulator/releases)
[![GitHub last commit (branch)](https://img.shields.io/github/last-commit/xscr33m/3D-Print_CostCulator/master?style=for-the-badge&color=gold)](https://github.com/xscr33m/3D-Print_CostCulator/commits/master/)
[![GitHub License](https://img.shields.io/github/license/xscr33m/3D-Print_CostCulator?style=for-the-badge&color=gold)](https://github.com/xscr33m/3D-Print_CostCulator/)
[![Discord](https://img.shields.io/discord/1102440447835648124?style=for-the-badge&label=Discord&color=gold)](https://discord.gg/5CrDj8ba6C)

<div align="center">
<h2>3D-Print CostCulator</p>
<img src="assets/icon.png" alt="3D-Print CostCulator" width="96" height="96">
<br>
</div>

_A professional tool for precise calculation of real 3D printing costs_

View this document in your preferred language:
[English](#english) | [Deutsch](#deutsch)

</div>

---

## English

### 📋 Overview

3D-Print CostCulator is a comprehensive desktop application designed to calculate the true costs of 3D printing projects. Unlike simple calculators, this tool considers multiple cost factors including materials, electricity consumption, and equipment wear to provide accurate cost estimates.

### ✨ Features

- **Multi-language Support**: Complete English and German interface
- **Comprehensive Cost Analysis**:
  - Material costs (filament consumption)
  - Electricity costs (printer and dryer)
  - Automatic wear & maintenance calculations
- **Equipment Management**:
  - Configurable printer profiles with power consumption
  - Filament database with cost per kg
  - Optional filament dryer support
- **Project Management**:
  - Save and load project files
  - Professional PDF export for quotations
  - Project history tracking
- **Professional PDF Reports**:
  - Detailed cost breakdowns
  - Professional quotation format
  - Multi-language report generation

### 🎯 Use Cases

- **Hobbyists**: Calculate actual printing costs for personal projects
- **Small Businesses**: Generate professional quotes for customers
- **Makerspaces**: Track and allocate printing costs
- **Educational**: Understand the economics of 3D printing

### 📥 Installation

#### Option 1: Pre-built Executable (Recommended)

1. Download the latest release from the `release/` folder
2. Run `3D-Print_CostCulator.exe` directly
3. No additional installation required

#### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/xscr33mlabs/3D-Print_CostCulator.git
cd 3D-Print_CostCulator

# Install dependencies
pip install -r requirements.txt

# Run the application
cd src
py main.py
```

### 🚀 Quick Start

1. **Launch the Application**

   - Run the executable or run `py main.py` in Terminal/CMD
   - No installation needed for the executable

2. **Set Up Your Equipment**

   - Add your 3D printer with power consumption (Watts)
   - Add filaments with cost per kg
   - Optionally add a filament dryer

3. **Create a Project**

   - Enter project and model names
   - Specify number of models and print duration
   - Select filament and enter consumption amount
   - Set electricity rate (€/kWh)

4. **Calculate Costs**

   - Click "Calculate Print Costs"
   - Review detailed cost breakdown
   - Export professional PDF report

### 📊 Cost Calculation Details

The application uses a sophisticated cost model:

- **Material Costs**: Based on actual filament consumption and price per kg
- **Electricity Costs**: Calculated from device power consumption and print time
- **Wear & Maintenance**: Automatic calculation based on:
  - Mechanical wear: 0.01% of material costs per gram
  - Time-based wear: €0.05 per hour of print time
  - Electronic wear: 0.5% of electricity costs

### 🛠️ Technical Requirements

- **Operating System**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: 3.8+ (if running from source)
- **Dependencies**: ReportLab (for PDF generation)
- **Storage**: ~50MB disk space

### 📁 Project Structure

```
3D-Print_CostCulator/
├── src/
│   ├── main.py                 # Main application
│   ├── language_manager.py     # Internationalization
│   └── translations/           # Language files
│       ├── en.json
│       └── de.json
├── release/                    # Built executables
├── build.py                    # Build script
├── requirements.txt            # Python dependencies
└── README                      # This file
```

### 🔧 Building from Source

```bash
# Install build dependencies
pip install pyinstaller

# Build executable
py build.py
```

### 🌐 Supported Languages

- English (en)
- Deutsch (de)

Additional languages can be added by creating translation files in `src/translations/`.

---

## Deutsch

### 📋 Überblick

Der 3D-Print CostCulator ist eine umfassende Desktop-Anwendung zur präzisen Berechnung der realen Kosten von 3D-Druck-Projekten. Im Gegensatz zu einfachen Rechnern berücksichtigt dieses Tool mehrere Kostenfaktoren wie Material, Stromverbrauch und Geräteverschleiß.

### ✨ Funktionen

- **Mehrsprachige Unterstützung**: Vollständige deutsche und englische Benutzeroberfläche
- **Umfassende Kostenanalyse**:
  - Materialkosten (Filamentverbrauch)
  - Stromkosten (Drucker und Trockner)
  - Automatische Verschleiß- und Wartungsberechnung
- **Geräteverwaltung**:
  - Konfigurierbare Druckerprofile mit Stromverbrauch
  - Filament-Datenbank mit Kosten pro kg
  - Optionale Filament-Trockner Unterstützung
- **Projektverwaltung**:
  - Speichern und Laden von Projektdateien
  - Professioneller PDF-Export für Kostenvoranschläge
  - Projekt-Verlaufsverfolgung
- **Professionelle PDF-Berichte**:
  - Detaillierte Kostenaufschlüsselung
  - Professionelles Angebots-Format
  - Mehrsprachige Berichtsgenerierung

### 🎯 Anwendungsbereiche

- **Hobby-Bereich**: Echte Druckkosten für private Projekte berechnen
- **Kleinbetriebe**: Professionelle Angebote für Kunden erstellen
- **Makerspaces**: Druckkosten verfolgen und zuordnen
- **Bildung**: Die Wirtschaftlichkeit des 3D-Drucks verstehen

### 📥 Installation

#### Option 1: Vorgefertigte Anwendung (Empfohlen)

1. Neueste Version aus dem `release/` Ordner herunterladen
2. `3D-Print_CostCulator.exe` direkt ausführen
3. Keine weitere Installation erforderlich

#### Option 2: Aus Quellcode ausführen

```bash
# Repository klonen
git clone https://github.com/xscr33mlabs/3D-Print_CostCulator.git
cd 3D-Print_CostCulator

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
cd src
py main.py
```

### 📊 Details zur Kostenberechnung

Die Anwendung verwendet ein ausgeklügeltes Kostenmodell:

- **Materialkosten**: Basierend auf tatsächlichem Filamentverbrauch und Preis pro kg
- **Stromkosten**: Berechnet aus Gerätestromverbrauch und Druckzeit
- **Verschleiß & Wartung**: Automatische Berechnung basierend auf:
  - Mechanischer Verschleiß: 0,01% der Materialkosten pro Gramm
  - Zeitbasierter Verschleiß: 0,05€ pro Stunde Druckzeit
  - Elektronischer Verschleiß: 0,5% der Stromkosten

---

### 📄 License

This project is licensed under the Creative Commons Attribution-NoDerivatives 4.0 International License. You are free to use this software, but you may not distribute modified versions or use it under a different name.

See the [LICENSE](LICENSE) file for details.

### 👨‍💻 Author

**xscr33mLabs** © 2025

### 🤝 Support

For support, questions, or feature requests, please visit our homepage or contact us through the application's about dialog.

### 💝 Donations

If you find this tool useful, consider supporting development:

- [Buy me a coffee](https://ko-fi.com/xscr33m)

---

<div align="center">
<small>Made with ❤️ for the 3D printing community</small>
</div>
