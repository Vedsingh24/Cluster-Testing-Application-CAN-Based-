# Cluster Testing Application

The **Cluster Testing Application** is a graphical tool designed for testing and manipulating CAN signals. This tool allows you to interface with various CAN bus hardware, send signals, and test cluster behavior based on loaded DBC (CAN Database) files. It provides an intuitive user interface for configuring interfaces, cycling messages, and toggling signals on or off.

---

## Features:
- **DBC File Support**: Load and parse DBC files to view and manipulate CAN signals for testing purposes.
- **CAN Bus Interface Support**: Supports multiple CAN interfaces, including:
  - Peak CAN
  - Kvaser CAN
  - Chuangxin USBCAN
  - Virtual CAN
- **Signal Control**:
  - Toggle signals on or off individually.
  - Auto-increment signal values or manually control them.
  - Set cycle times for CAN message transmissions.
  - Support for "Toggle All" controls to activate or deactivate all signals at once.
- **Customizable Cycle Times**: Global settings for message cycle times (e.g., 10ms, 50ms, 100ms, etc.).
- **Error Notifications**: Built-in error handling with user-friendly messages for invalid inputs or hardware issues.
- **Scroll and Search Signals**: User-friendly layout with scrollable areas for managing large numbers of signals.

---

## System Requirements:
- **Python**: Python 3.11 or later.
- **Required Libraries**:
  Install the necessary Python packages:
  ```bash
  pip install python-can cantools tkinter
  ```

---

## Usage:
1. **Load a DBC File**:
   - Click "Load DBC" and select your DBC file to parse and display available CAN signals.
2. **Configure the CAN Interface**:
   - Select the desired CAN interface (e.g., Peak CAN, Kvaser CAN) from the dropdown menu.
   - Choose the bitrate for your CAN bus (e.g., 125 kbps, 500 kbps, etc.).
   - Click **Start Interface** to initialize the CAN connection.
3. **Control Signals**:
   - Use toggle buttons to turn signals on or off.
   - Enter specific values into the corresponding signal entry box for manual control, or use the "A" option for auto-incrementing.
   - Use the "Toggle All ON" or "Toggle All OFF" controls for bulk signal management.
4. **Set Cycle Time**:
   - Configure the global cycle time using the provided radio buttons to define how often messages are transmitted.
5. **Monitor CAN Traffic**:
   - The app sends configured signals cyclically to the CAN bus, simulating real-world cluster testing scenarios.

---

## Precautions:
- Ensure your CAN interface hardware is properly connected and compatible with the selected driver/interface.
- Load a valid DBC file for accurate signal definitions.
- Incorrect or invalid configuration (e.g., missing DBC file or invalid signal input) will result in error messages.

---

## Supported CAN Interfaces:
The application supports various CAN hardware interfaces. Ensure the required drivers are installed for your system:
- **Peak CAN**
- **Kvaser CAN**
- **Chuangxin USBCAN**
- **Virtual CAN** (for testing purposes)

---

## Troubleshooting:
- **DBC Loading Errors**:
  Ensure the selected DBC file is valid and properly formatted.
- **Interface Connection Errors**:
  Double-check hardware connections, drivers, and configurations in the app.
- **Signal Issues**:
  If signal toggles don't work, verify that the interface is properly initialized and a DBC file is loaded.

---

This tool simplifies the process of sending CAN signals for testing clusters or components in automotive applications. It provides full control over signal manipulation and automated testing scenarios.

**Happy Testing!**
