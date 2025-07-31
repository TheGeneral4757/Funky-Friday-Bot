# Funky Friday Bot

An automated note detection and key pressing bot for rhythm games like Friday Night Funkin'. Detects colored notes on screen and automatically presses the corresponding keys with configurable timing and accuracy.

## What It Does

- **Screen Scanning**: Continuously monitors a specific region of your screen for colored notes
- **Color Detection**: Uses RGB color matching to identify when notes appear
- **Automatic Key Pressing**: Simulates keyboard input when notes are detected
- **Live Statistics**: Shows real-time performance metrics and system stats
- **Pause/Resume**: Can be paused and resumed without restarting
- **Configurable**: Easy to adjust timing, colors, and key bindings

## Requirements

### System Requirements
- **Windows 10/11** (tested on Windows)
- **Python 3.8+** installed
- **Administrator privileges** (for keyboard simulation)

### Python Dependencies
Install all required packages with this command:

```bash
pip install keyboard numpy mss pydirectinput psutil pyautogui rich
```

## Quick Setup

### 1. Download and Install
1. Download the project files (`fnf-player.py`, `config.json`, `README.md`)
2. Open Command Prompt as Administrator
3. Navigate to the project folder
4. Install dependencies: `pip install keyboard numpy mss pydirectinput psutil pyautogui rich`

### 2. Configure for Your Game
1. Open `config.json` in any text editor
2. Update the note positions and colors (see Configuration section below)
3. Adjust key bindings to match your game
4. Save the file

### 3. Run the Bot
1. Start your rhythm game
2. Position the game window where the bot expects it
3. Run: `python fnf-player.py`
4. Press `P` to pause/resume, `ESC` to exit

## Configuration Guide

### Finding Note Positions and Colors

**Method 1: Using a Color Picker**
1. Take a screenshot of your game during gameplay
2. Use a color picker tool (like Windows Snipping Tool or online color pickers)
3. Click on each note when it should be pressed
4. Note the X, Y coordinates and RGB values

**Method 2: Trial and Error**
1. Start with approximate positions
2. Run the bot and watch the debug output
3. Adjust coordinates and colors until detection works

### Config.json Settings Explained

```json
{
  "//": "=== TIMING SETTINGS ===",
  "BASE_DELAY_MS": 50,        // Scanner loop delay (lower = faster response)
  "RELEASE_DELAY_MS": 20,     // How long to hold each key (milliseconds)
  "HIT_DELAY_MS": 0,          // Extra delay before pressing (for timing adjustment)
  
  "//": "=== DETECTION SETTINGS ===",
  "COLOR_TOLERANCE": 40,       // Color matching tolerance (0-255, higher = more lenient)
  "PADDING": 2,               // Extra pixels around note detection areas
  
  "//": "=== NOTE POSITIONS (X, Y coordinates) ===",
  "NOTE_COORDS": {
    "left":  [300, 210],      // Left arrow position
    "down":  [530, 210],      // Down arrow position
    "up":    [750, 210],      // Up arrow position
    "right": [980, 210]       // Right arrow position
  },
  
  "//": "=== NOTE COLORS (R, G, B values) ===",
  "NOTE_COLORS": {
    "left":  [194, 75, 153],  // RGB color of left note
    "up":    [18, 250, 4],    // RGB color of up note
    "down":  [0, 255, 255],   // RGB color of down note
    "right": [249, 56, 62]    // RGB color of right note
  },
  
  "//": "=== KEY BINDINGS ===",
  "KEY_BINDINGS": {
    "left":  "a",             // Key for left arrow
    "down":  "s",             // Key for down arrow
    "up":    "w",             // Key for up arrow
    "right": "d"              // Key for right arrow
  },
  
  "//": "=== CONTROL SETTINGS ===",
  "FAILSAFE_KEY": "esc",      // Emergency exit key
  "DEBUG": true,              // Show detailed console logs
  
  "//": "=== DEBUG PANEL SETTINGS ===",
  "DEBUG_PANEL": {
    "enabled": true,          // Show live status panel
    "show_paused": true,      // Show pause status
    "show_keypresses": true,  // Show keypress count
    "show_last_action": true, // Show last action
    "show_uptime": true,      // Show running time
    "show_fps": true,         // Show scanner FPS
    "show_cpu": true,         // Show CPU usage
    "show_memory": true,      // Show memory usage
    "show_config": true       // Show current config
  }
}
```

## Troubleshooting

### Common Issues

**Bot doesn't detect notes:**
- Check that note positions are correct
- Verify RGB colors match your game
- Increase `COLOR_TOLERANCE` if lighting varies
- Make sure game window is in the expected position

**Bot presses keys too early/late:**
- Adjust `HIT_DELAY_MS` for timing
- Modify `RELEASE_DELAY_MS` for key hold duration
- Fine-tune `BASE_DELAY_MS` for responsiveness

**High CPU usage:**
- Increase `BASE_DELAY_MS` to reduce scan frequency
- Disable debug panel if not needed
- Close other programs to free resources

**Keys not being pressed:**
- Run as Administrator
- Check that key bindings match your game
- Verify `pydirectinput` is working properly

### Performance Tips

- **Lower `BASE_DELAY_MS`** for faster response (but higher CPU usage)
- **Higher `COLOR_TOLERANCE`** for more lenient detection
- **Disable debug panel** if you don't need live stats
- **Close unnecessary programs** to free up system resources

## Controls

- **P**: Pause/Resume the bot
- **ESC**: Emergency exit (failsafe)
- **Debug Panel**: Shows live statistics and status

## Legal Notice

This tool is for educational and personal use only. Use responsibly and in accordance with the terms of service of any games you use it with. The authors are not responsible for any consequences of using this software.

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all dependencies are installed
3. Ensure you're running as Administrator
4. Test with different timing settings

## Files Explained

- **`fnf-player.py`**: Main bot script with all the logic
- **`config.json`**: All settings and configuration
- **`README.md`**: This documentation file

---
