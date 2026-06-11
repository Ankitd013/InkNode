<div align="center">

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-orange.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Raspberry_Pi-c2185b.svg)](https://www.raspberrypi.org/)

<img src="assets/logo.svg" alt="InkNode Logo" width="300" />

<h3 align="center">A clean, distraction-free room climate monitor and home automation dashboard for the Raspberry Pi</h3>
</div>

<img src="assets/inknode-screen.png" alt="InkNode Screen"/>

## 📖 What is InkNode?

InkNode gives you complete visibility into your home environment without adding another glowing screen to your life. If you want smart home data on your desk or nightstand but are tired of bright backlights, InkNode is the solution. It is a self-contained appliance that reads local ambient conditions via hardware sensors, pulls outdoor forecasts, and displays them on a calm, paper-like electronic ink display.

Operating as an independent node, it provides a local web interface for effortless configuration and streams live telemetry directly to your existing home automation server over MQTT.

## ✨ Core Pillars of InkNode

To deliver a seamless and calm experience, InkNode is built on three main principles: Distraction-Free Design, Frictionless Setup, and Flexible Architecture.

### Distraction-Free Design
- **High-Contrast, Swiss-Style UI:** A borderless layout inspired by classic minimalist design prioritizes clean typography and readability.

- **Smart Color Layering:** Intentionally utilizes the e-paper's red ink for abstract weather icons and metric labels (`WIND`, `HUM`), preserving heavy black ink for critical data.


### Frictionless Setup (Zero Headaches)

- **Automated Headless Provisioning:** Forget about plugging in a monitor, keyboard, or manually editing configuration files on an SD card.

- **Captive Setup Portal:** If InkNode cannot reach the internet on boot, it automatically launches a temporary Wi-Fi Access Point and displays a QR code on the e-paper screen. Scan it, enter your credentials in the local web portal, and you are online.

- **Safe Rollbacks:** If a connection to your router fails, a background thread safely aborts and restores the setup portal so you are never locked out of your device.
    
### Flexible Architecture
- **Local Web Dashboard:** Tweak geographic coordinates, customize panel headers, or update MQTT broker targets directly from your browser.

- **Hot Reloading:** Saving changes automatically updates the system environment (`.env`) and restarts background loops immediately—no reboot required.

- **Hardware Agnostic (HAL):** Display and sensor logic are cleanly isolated. You can easily swap the default 2.9" Waveshare drivers or AHTx0 code to support alternative I2C sensors (like the BME280) or different display sizes.

- **Pre-Deployment Testing:** Test layout calculations and logic on your PC using mocked hardware states before deploying to a physical Raspberry Pi.

### 📡 Decoupled Hardware & Automation

-   **Hardware Agnostic (HAL):** The core display and sensor handling logic are cleanly isolated in `hal_display.py` and `hal_sensors.py`. You can easily swap out the default 2.9" Waveshare drivers or the AHTx0 code to support completely different display sizes or alternative I2C sensors (like the BME280 or DHT22).
    
-   **Pre-Deployment Testing:** Includes an independent test runner (`run_tests.py`) that uses mocked hardware states. This lets you test the layout calculations and application logic on a standard PC before deploying the code to a physical Pi.
    
## ⚙️ System Architecture: Under the Hood

InkNode manages simultaneous background processes while ensuring the UI remains responsive and independent of network or hardware delays.

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

## 🛠️ Hardware Specifications & Wiring

### What You Need

To build a standalone InkNode device, gather the following components:

1. **Raspberry Pi** Zero W or Zero 2W (ideal for a compact footprint).

2. **Waveshare 2.9" E-Paper Module:** Must be the Black/White/Red Tri-Color version.

3. **AHT25 or AHT20 Sensor:** I2C digital temperature and humidity module.

4. **MicroSD Card:** 8GB or larger running Raspberry Pi OS Lite (32/64-bit).

### Wiring Diagram

Connect your Waveshare 2.9inch e-Paper Module (B) to your Raspberry Pi using the physical SPI pin layout mapped below.

(For complete technical specifications, refer directly to the [Official Waveshare 2.9inch e-Paper Module (B) Manual.](https://www.waveshare.com/wiki/2.9inch_e-Paper_Module_(B)_Manual))

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

### 1. Enable Hardware Interfaces

Ensure the necessary hardware communication buses are active on your Raspberry Pi.

1. Run `sudo raspi-config` in your terminal.

2. Navigate to Interface Options.

3. Enable both `SPI` and `I2C`

### 2. Install and Execute

Clone the repository and run the setup script to install dependencies and configure the environment automatically.

```bash
git clone https://github.com/Ankitd013/InkNode.git
cd InkNode

chmod +x setup.sh
sudo ./setup.sh
```