<div align="center">
  <img src="assets/logo.svg" alt="InkNode Logo" width="180" />

# InkNode

**A clean, distraction-free room climate monitor and home automation dashboard for the Raspberry Pi.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-orange.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Raspberry_Pi-c2185b.svg)](https://www.raspberrypi.org/)

</div>

---

## 📖 What is InkNode?

InkNode is a self-contained smart home appliance that acts as a dedicated environment dashboard. It reads local ambient conditions using a precise hardware sensor, pulls outdoor forecasts, and displays them on a paper-like electronic ink display. 

With no bright backlights or glowing screens, it fits comfortably on a desk or nightstand. Under the hood, it functions as an independent node in your smart home setup—running a local web interface for easy configuration and streaming live telemetry straight to your existing home automation server over MQTT.

---

## ⚙️ How It Works

```mermaid
graph TD
    %% Styling
    classDef script fill:#1f1f1f,stroke:#E63946,stroke-width:2px,color:#fff;
    classDef hardware fill:#e1dbcd,stroke:#333,stroke-width:2px,color:#000;
    classDef external fill:#fbfbfb,stroke:#0052cc,stroke-width:1px,color:#000;

    %% Elements
    BOOT[boot_manager.py]:::script
    CONF[config.py]:::script
    DASH[dashboard.py / Flask]:::script
    MQTT[mqtt_engine.py]:::script
    WEATH[weather_api.py]:::script
    
    SENS[hal_sensors.py]:::script
    DISP[hal_display.py]:::script
    WAVE[waveshare_epd]:::script
    
    AHT[AHT10/20 Hardware Sensor]:::hardware
    EPD[2.9 inch E-Paper Screen]:::hardware
    
    OM[Open-Meteo API]:::external
    BROK[MQTT Broker / Home Assistant]:::external
    BROW[User Web Browser]:::external

    %% Flow Layout
    BOOT -->|1. Reads profiles| CONF
    
    %% Boot Decision Fork
    BOOT -->|2. Tests Network Connection| CHECK{Internet Available?}
    
    CHECK -->|No| PORTAL[Launch Captive AP Portal]
    PORTAL -->|Draws Onboarding QR| DISP
    BROW <-->|Configures Wi-Fi via Port 80| DASH
    DASH -->|Writes updates & reboots| CONF
    
    CHECK -->|Yes| RUN[Initialize Runtime Engines]
    
    %% Runtime Concurrent Engines
    subgraph Background Execution Threads
        RUN --> DASH
        RUN --> MQTT
    end

    %% Data Harvesting Interconnectivity
    DASH <-->|Inter-process State| BOOT
    SENS -->|Polls Raw Data via I2C| AHT
    WEATH -->|Fetches Live Forecast via HTTPS| OM
    
    %% Aggregation
    BOOT -->|Requests Updates| SENS
    BOOT -->|Requests Updates| WEATH
    
    %% Output Routing
    BOOT -->|Composes Geometric Canvas| DISP
    DISP -->|Low-Level SPI Calls| WAVE
    WAVE -->|Refreshes Matrix Layers| EPD
    
    MQTT -->|Publishes Formatted JSON| BROK
    BROW <-->|Manages Settings / Dynamic .env| DASH
```

## ✨ Core Features

### 🎨 Clean Swiss-Style UI

-   **High Contrast Hierarchy:** A borderless layout inspired by classic minimalist design principles, focusing entirely on clean typography.
    
-   **Smart Color Layering:** Uses the e-paper's red ink layer intentionally for abstract weather icons and metric labels (`WIND`, `HUM`), leaving heavy black ink for easy-to-read numbers.

### 🔌 Headless Wi-Fi Provisioning

-   **No Headaches on First Boot:** You don't need to plug in a monitor or keyboard, and you don't need to write configuration files to your SD card.
    
-   **Automated Setup Portal:** If InkNode cannot reach the internet on boot, it switches its Wi-Fi card into a temporary Access Point and displays a setup QR code on the e-paper screen. Scanning it opens a local web interface where you can securely type in your Wi-Fi credentials.
    
-   **Safe Rollback:** If the connection to your router fails, a background thread cleanly safely aborts and restores the setup portal so you aren't locked out.
    

### 📱 Local Web Dashboard

-   **Web UI Configuration:** Once connected to your local network, typing the device's IP address into a browser opens a clean dashboard.
    
-   **On-the-Fly Editing:** Tweak your geographic coordinates, set custom panel headers, or update your MQTT broker targets directly from your browser.
    
-   **Hot Reloading:** Saving changes automatically updates the system environment (`.env`) and restarts background loops immediately without needing a full system reboot.
    

### 📡 Decoupled Hardware & Automation

-   **Hardware Agnostic (HAL):** The core display and sensor handling logic are cleanly isolated in `hal_display.py` and `hal_sensors.py`. You can easily swap out the default 2.9" Waveshare drivers or the AHTx0 code to support completely different display sizes or alternative I2C sensors (like the BME280 or DHT22).
    
-   **Pre-Deployment Testing:** Includes an independent test runner (`run_tests.py`) that uses mocked hardware states. This lets you test the layout calculations and application logic on a standard PC before deploying the code to a physical Pi.
    

## 🛠️ Hardware Requirements

To build a standalone InkNode device, you will need:

1.  **Raspberry Pi** (Zero W or Zero 2 W are ideal for a compact footprint)
    
2.  **Waveshare 2.9" E-Paper Module** (Must be the Black/White/Red Tri-Color version)
    
3.  **AHT25 or AHT20 Sensor** (I2C digital temperature and humidity module)
    
4.  **MicroSD Card** (8GB or larger) running Raspberry Pi OS Lite (32/64-bit)

## 🛠️ Hardware Wiring

To assemble a standalone InkNode device, connect your **Waveshare 2.9inch e-Paper Module (B)** tri-color display to your Raspberry Pi using the physical SPI pin layout below. 

For complete technical specifications and hardware driver updates, refer directly to the [Official Waveshare 2.9inch e-Paper Module (B) Manual](https://www.waveshare.com/wiki/2.9inch_e-Paper_Module_(B)_Manual).

```mermaid
graph LR
    %% Styling Configuration
    classDef epaper fill:#fff,stroke:#E63946,stroke-width:2px,color:#000;
    classDef rpi fill:#1f1f1f,stroke:#c2185b,stroke-width:2px,color:#fff;
    classDef pwr fill:#ffcccc,stroke:#cc0000,stroke-width:1px,color:#000;
    classDef gnd fill:#e1e1e1,stroke:#666,stroke-width:1px,color:#000;
    classDef spi fill:#e1f5fe,stroke:#03a9f4,stroke-width:1px,color:#000;
    classDef ctrl fill:#e8f5e9,stroke:#4caf50,stroke-width:1px,color:#000;

    subgraph Waveshare 2.9in Module B Pi Hat / Cable
        VCC[VCC - 3.3V / Red Wire]:::pwr
        GND_E[GND - Ground / Black Wire]:::gnd
        DIN[DIN - SPI MOSI / Blue Wire]:::spi
        CLK[CLK - SPI SCLK / Yellow Wire]:::spi
        CS[CS - Chip Select / Orange Wire]:::spi
        DC[DC - Data/Command / Green Wire]:::ctrl
        RST[RST - Reset / White Wire]:::ctrl
        BUSY[BUSY - Status / Purple Wire]:::ctrl
    end

    subgraph Raspberry Pi 40-Pin GPIO Header
        P3V3[3.3V Power - Physical Pin 1]:::pwr
        PGND[GND Ground - Physical Pin 6]:::gnd
        BCM10[BCM 10 / MOSI - Physical Pin 19]:::spi
        BCM11[BCM 11 / SCLK - Physical Pin 23]:::spi
        BCM8[BCM 8 / CE0 - Physical Pin 24]:::spi
        BCM25[BCM 25 - Physical Pin 22]:::ctrl
        BCM17[BCM 17 - Physical Pin 11]:::ctrl
        BCM24[BCM 24 - Physical Pin 18]:::ctrl
    end

    %% Wiring Connections
    VCC  <===> |Power Rail| P3V3
    GND_E <===> |Ground Reference| PGND
    DIN  <---> |Data Input| BCM10
    CLK  <---> |Clock Input| BCM11
    CS   <---> |Chip Selection| BCM8
    DC   <---> |Data/Command Control| BCM25
    RST  <---> |External Reset| BCM17
    BUSY <---> |Busy Status Output| BCM24
```

## 🚀 Getting Started

### 1. Prepare Your Interfaces

Make sure the necessary hardware communication buses are enabled. Run `sudo raspi-config`, navigate to **Interface Options**, and ensure both **SPI** and **I2C** are active.

### 2. Installation

Clone the repository to your Raspberry Pi and execute the included setup script:

```bash
git clone https://github.com/Ankitd013/InkNode.git
cd InkNode

chmod +x setup.sh
sudo ./setup.sh
```