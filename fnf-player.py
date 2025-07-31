import os
import time
import threading
import json
import numpy as np
import mss
import pydirectinput
import keyboard
import psutil
import pyautogui
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TextColumn
import shutil

# =============================================================================
# FNF TURBO BOT - AUTOMATIC NOTE DETECTION AND PRESSING
# =============================================================================
# This bot detects colored notes on screen and automatically presses the
# corresponding keys. It's designed for Friday Night Funkin' but can work
# with any rhythm game that uses colored notes.
# =============================================================================

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION LOADING
# ──────────────────────────────────────────────────────────────────────────────
# Load all settings from config.json file
with open("config.json", "r") as f:
    cfg = json.load(f)

# Extract timing settings
BASE_DELAY_MS    = cfg.get("BASE_DELAY_MS", 50)      # Scanner loop delay
RELEASE_DELAY_MS = cfg.get("RELEASE_DELAY_MS", 20)   # How long to hold keys
HIT_DELAY_MS     = cfg.get("HIT_DELAY_MS", 0)       # Extra delay before pressing

# Extract detection settings
TOLERANCE        = cfg.get("COLOR_TOLERANCE", 40)     # Color matching tolerance
PADDING          = cfg.get("PADDING", 2)              # Extra pixels around notes
FAILSAFE_KEY     = cfg.get("FAILSAFE_KEY", "esc")    # Emergency exit key
DEBUG            = cfg.get("DEBUG", False)            # Enable debug logging

# Extract note detection data
NOTE_COORDS  = {d: tuple(v) for d, v in cfg["NOTE_COORDS"].items()}   # Screen positions
NOTE_COLORS  = {d: tuple(v) for d, v in cfg["NOTE_COLORS"].items()}   # RGB colors
KEY_BINDINGS = cfg.get("KEY_BINDINGS", {})                             # Key mappings

# Verify all config sections have the same keys
assert NOTE_COORDS.keys() == NOTE_COLORS.keys() == KEY_BINDINGS.keys(), "Config keys mismatch"

# Create mapping: (x, y) position -> (key_to_press, target_color)
KEY_MAP = {NOTE_COORDS[d]: (KEY_BINDINGS[d], NOTE_COLORS[d]) for d in NOTE_COORDS}

# ──────────────────────────────────────────────────────────────────────────────
# SCREEN CAPTURE REGION CALCULATION
# ──────────────────────────────────────────────────────────────────────────────
# Calculate the smallest rectangle that contains all note positions
xs = [x for x, y in KEY_MAP]
ys = [y for x, y in KEY_MAP]
left   = min(xs) - PADDING
top    = min(ys) - PADDING
right  = max(xs) + PADDING + 1
bottom = max(ys) + PADDING + 1

# Define the capture region for screen grabbing
CAPTURE_BOX = {"left": left, "top": top, "width": right - left, "height": bottom - top}

# Convert absolute coordinates to relative coordinates within capture region
REL_COORDS = {pt: (pt[0] - left, pt[1] - top) for pt in KEY_MAP}

# ──────────────────────────────────────────────────────────────────────────────
# DEBUG PANEL SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
DEBUG_PANEL = cfg.get("DEBUG_PANEL", {})
DEBUG_PANEL_ENABLED = DEBUG_PANEL.get("enabled", True)
DEBUG_UPDATE_RATE = cfg.get("DEBUG_UPDATE_RATE", 0.05)

# ──────────────────────────────────────────────────────────────────────────────
# STATISTICS TRACKING
# ──────────────────────────────────────────────────────────────────────────────
stats = {
    "paused": False,
    "keypresses": 0,
    "last_action": "",
    "start_time": time.time(),
    "fps": 0,
    "debug_messages": [],  # New: store debug messages
    "last_debug_time": time.time(),
}

def update_stats(paused=None, keypress=None, last_action=None, fps=None):
    """
    Update the global statistics
    
    Args:
        paused: New paused state
        keypress: Whether a key was just pressed
        last_action: Description of the last action
        fps: Current frames per second
    """
    if paused is not None:
        stats["paused"] = paused
    if keypress:
        stats["keypresses"] += 1
    if last_action is not None:
        stats["last_action"] = last_action
    if fps is not None:
        stats["fps"] = fps

# ──────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────
def debug_log(msg):
    """Add debug messages to the stats instead of printing them"""
    if DEBUG:
        current_time = time.time()
        timestamp = time.strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {msg}"
        
        # Add to debug messages list (keep last 5 messages)
        stats["debug_messages"].append(formatted_msg)
        if len(stats["debug_messages"]) > 5:
            stats["debug_messages"].pop(0)
        
        stats["last_debug_time"] = current_time
        stats["last_action"] = msg  # Also update last action

# ──────────────────────────────────────────────────────────────────────────────
# STARTUP MESSAGES
# ──────────────────────────────────────────────────────────────────────────────
debug_log("🚀 FNF Turbo Bot | PRESS-RELEASE + DEBUG MODE STARTED 🚀")
debug_log(f"Region: {CAPTURE_BOX}, Tolerance: ±{TOLERANCE}, Hold Time: {RELEASE_DELAY_MS}ms")
debug_log("Focus game window and hold ESC to abort.")
time.sleep(1)

# ──────────────────────────────────────────────────────────────────────────────
# KEY PRESSING FUNCTION
# ──────────────────────────────────────────────────────────────────────────────
def hold_key_temporarily(key, hold_time, hit_delay=0):
    """
    Press and hold a key for a specified duration
    
    Args:
        key: The key to press (e.g., 'a', 's', 'w', 'd')
        hold_time: How long to hold the key in milliseconds
        hit_delay: Additional delay before pressing in milliseconds
    """
    # Apply hit delay if specified (for timing adjustments)
    if hit_delay > 0:
        time.sleep(hit_delay / 1000.0)
    
    debug_log(f"Pressing key '{key}'")
    pydirectinput.keyDown(key)
    time.sleep(hold_time / 1000.0)
    pydirectinput.keyUp(key)
    debug_log(f"Released key '{key}'")
    update_stats(keypress=True, last_action=f"Pressed {key}")

# ──────────────────────────────────────────────────────────────────────────────
# PAUSE/RESUME SYSTEM
# ──────────────────────────────────────────────────────────────────────────────
paused = False

def toggle_pause():
    """Toggle between paused and running states"""
    global paused
    paused = not paused
    update_stats(paused=paused, last_action="Paused" if paused else "Resumed")
    debug_log("Paused" if paused else "Resumed")

# Set up hotkey for pause/resume
keyboard.add_hotkey('p', toggle_pause)  # Press 'p' to pause/resume

# ──────────────────────────────────────────────────────────────────────────────
# DEBUG PANEL UI
# ──────────────────────────────────────────────────────────────────────────────
def make_stats_panel():
    """Create a detailed live-updating status panel with comprehensive information"""
    table = Table.grid()
    
    # ─── STATUS SECTION ───
    status_color = "red" if stats["paused"] else "green"
    status_icon = "⏸️" if stats["paused"] else "▶️"
    status_text = "PAUSED" if stats["paused"] else "RUNNING"
    table.add_row(f"[bold {status_color}]{status_icon} {status_text}[/bold {status_color}]")
    
    # ─── PERFORMANCE METRICS ───
    table.add_row("")  # Spacer
    table.add_row("[bold cyan]PERFORMANCE METRICS[/bold cyan]")
    table.add_row(f"[bold]Keypresses:[/bold] {stats['keypresses']:,}")
    table.add_row(f"[bold]Last Action:[/bold] {stats['last_action']}")
    
    # Calculate and display uptime in a nice format
    uptime_seconds = int(time.time() - stats['start_time'])
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    if hours > 0:
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        uptime_str = f"{minutes:02d}:{seconds:02d}"
    table.add_row(f"[bold]Uptime:[/bold] {uptime_str}")
    
    # ─── SYSTEM PERFORMANCE ───
    table.add_row("")  # Spacer
    table.add_row("[bold yellow]SYSTEM PERFORMANCE[/bold yellow]")
    
    # FPS with color coding
    fps = stats['fps']
    fps_color = "red" if fps < 30 else "yellow" if fps < 60 else "green"
    table.add_row(f"[bold]Scanner FPS:[/bold] [{fps_color}]{fps:.1f}[/{fps_color}]")
    
    # CPU with detailed info
    cpu = psutil.cpu_percent()
    cpu_color = "red" if cpu > 80 else "yellow" if cpu > 50 else "green"
    cpu_freq = psutil.cpu_freq()
    cpu_freq_str = f"{cpu_freq.current/1000:.1f}GHz" if cpu_freq else "N/A"
    table.add_row(f"[bold]CPU Usage:[/bold] [{cpu_color}]{cpu}%[/{cpu_color}] ({cpu_freq_str})")
    
    # Memory with detailed info
    mem = psutil.virtual_memory()
    mem_color = "red" if mem.percent > 80 else "yellow" if mem.percent > 50 else "green"
    mem_used_gb = mem.used / (1024**3)
    mem_total_gb = mem.total / (1024**3)
    table.add_row(f"[bold]Memory:[/bold] [{mem_color}]{mem.percent}%[/{mem_color}] ({mem_used_gb:.1f}GB/{mem_total_gb:.1f}GB)")
    
    # ─── BOT CONFIGURATION ───
    table.add_row("")  # Spacer
    table.add_row("[bold magenta]BOT CONFIGURATION[/bold magenta]")
    table.add_row(f"[bold]Color Tolerance:[/bold] ±{TOLERANCE}")
    table.add_row(f"[bold]Base Delay:[/bold] {BASE_DELAY_MS}ms")
    table.add_row(f"[bold]Release Delay:[/bold] {RELEASE_DELAY_MS}ms")
    table.add_row(f"[bold]Hit Delay:[/bold] {HIT_DELAY_MS}ms")
    
    # ─── DETECTION REGION ───
    table.add_row("")  # Spacer
    table.add_row("[bold blue]DETECTION REGION[/bold blue]")
    table.add_row(f"[bold]Capture Box:[/bold] {CAPTURE_BOX['left']},{CAPTURE_BOX['top']} → {CAPTURE_BOX['left']+CAPTURE_BOX['width']},{CAPTURE_BOX['top']+CAPTURE_BOX['height']}")
    table.add_row(f"[bold]Region Size:[/bold] {CAPTURE_BOX['width']}×{CAPTURE_BOX['height']} pixels")
    
    # ─── NOTE MAPPINGS ───
    table.add_row("")  # Spacer
    table.add_row("[bold green]NOTE MAPPINGS[/bold green]")
    for direction in NOTE_COORDS.keys():
        key = KEY_BINDINGS[direction]
        color = NOTE_COLORS[direction]
        pos = NOTE_COORDS[direction]
        table.add_row(f"[bold]{direction.upper()}:[/bold] {key} → RGB{color} @ ({pos[0]},{pos[1]})")
    
    # ─── DEBUG MESSAGES ───
    table.add_row("")  # Spacer
    table.add_row("[bold white]DEBUG MESSAGES[/bold white]")
    if stats["debug_messages"]:
        for msg in stats["debug_messages"]:
            table.add_row(f"[dim]{msg}[/dim]")
    else:
        table.add_row("[dim]No debug messages yet...[/dim]")
    
    # ─── SYSTEM INFO ───
    table.add_row("")  # Spacer
    table.add_row("[bold white]SYSTEM INFO[/bold white]")
    
    # Disk usage
    try:
        disk = psutil.disk_usage('/')
        disk_color = "red" if disk.percent > 80 else "yellow" if disk.percent > 50 else "green"
        disk_free_gb = disk.free / (1024**3)
        table.add_row(f"[bold]Disk Usage:[/bold] [{disk_color}]{disk.percent}%[/{disk_color}] ({disk_free_gb:.1f}GB free)")
    except:
        table.add_row("[bold]Disk Usage:[/bold] N/A")
    
    # Network info
    try:
        net_io = psutil.net_io_counters()
        net_sent_mb = net_io.bytes_sent / (1024**2)
        net_recv_mb = net_io.bytes_recv / (1024**2)
        table.add_row(f"[bold]Network:[/bold] ↑{net_sent_mb:.1f}MB ↓{net_recv_mb:.1f}MB")
    except:
        table.add_row("[bold]Network:[/bold] N/A")
    
    # Process info
    process = psutil.Process()
    table.add_row(f"[bold]Process ID:[/bold] {process.pid}")
    table.add_row(f"[bold]Memory Usage:[/bold] {process.memory_info().rss / (1024**2):.1f}MB")
    
    # ─── CONTROLS ───
    table.add_row("")  # Spacer
    table.add_row("[bold yellow]CONTROLS[/bold yellow]")
    table.add_row("[bold]P:[/bold] Pause/Resume")
    table.add_row("[bold]ESC:[/bold] Emergency Exit")
    table.add_row("[bold]Debug Panel:[/bold] Live Status Display")
    
    # ─── PERFORMANCE TIPS ───
    table.add_row("")  # Spacer
    table.add_row("[bold cyan]PERFORMANCE TIPS[/bold cyan]")
    if fps < 30:
        table.add_row("[red]⚠️  Low FPS detected - consider increasing BASE_DELAY_MS[/red]")
    if cpu > 80:
        table.add_row("[red]⚠️  High CPU usage - close other programs[/red]")
    if mem.percent > 80:
        table.add_row("[red]⚠️  High memory usage - consider restarting[/red]")
    if stats['keypresses'] == 0:
        table.add_row("[yellow]💡 No keypresses detected - check note positions and colors[/yellow]")
    else:
        table.add_row(f"[green]✅ Bot is working! {stats['keypresses']} keypresses detected[/green]")
    
    return Panel(table, title="[bold]FNF TURBO BOT - DETAILED STATUS[/bold]", border_style="blue", padding=(1, 2))

def stats_ui():
    """Run the live-updating status panel"""
    if not DEBUG_PANEL_ENABLED:
        return
    
    console = Console()
    
    while True:
        # Clear the terminal (works on Windows)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Print the panel
        console.print(make_stats_panel())
        
        # Wait before next update (longer to reduce flickering)
        time.sleep(DEBUG_UPDATE_RATE)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN SCANNER THREAD
# ──────────────────────────────────────────────────────────────────────────────
def scanner():
    """
    Main scanning loop that detects notes and triggers key presses
    
    This function runs continuously and:
    1. Captures a region of the screen
    2. Checks each note position for the target color
    3. Presses the corresponding key when a note is detected
    4. Tracks performance statistics
    """
    sct = mss.mss()  # Screen capture object
    held_keys = set()  # Track which keys are currently held
    last_time = time.time()  # For FPS calculation
    frame_count = 0  # Frame counter for FPS

    while True:
        # Check for emergency exit
        if keyboard.is_pressed(FAILSAFE_KEY):
            debug_log("Failsafe hit. Exiting.")
            os._exit(0)

        # Skip processing if paused
        if paused:
            time.sleep(0.1)
            continue

        # Capture the screen region containing all notes
        img = np.array(sct.grab(CAPTURE_BOX))
        detected_keys = set()

        # Check each note position for color matches
        for orig, (key, target) in KEY_MAP.items():
            rx, ry = REL_COORDS[orig]  # Get relative coordinates
            hit = False
            
            # Check a 3x3 pixel area around the note position for better detection
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    x, y = rx + dx, ry + dy
                    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0]:
                        b, g, r, _ = img[y, x]  # Get RGB values (note: OpenCV uses BGR)
                        
                        # Check if color matches within tolerance
                        if (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255 and
                            abs(r - target[0]) <= TOLERANCE and
                            abs(g - target[1]) <= TOLERANCE and
                            abs(b - target[2]) <= TOLERANCE):
                            hit = True
                            break
                if hit:
                    detected_keys.add(key)
                    break

        # Press keys for newly detected notes
        for key in detected_keys - held_keys:
            if HIT_DELAY_MS > 0:
                time.sleep(HIT_DELAY_MS / 1000.0)
            threading.Thread(
                target=hold_key_temporarily,
                args=(key, RELEASE_DELAY_MS, HIT_DELAY_MS),
                daemon=True
            ).start()

        # Update tracking
        held_keys = detected_keys
        
        # Calculate and update FPS
        frame_count += 1
        now = time.time()
        if now - last_time >= 1.0:
            update_stats(fps=frame_count / (now - last_time))
            frame_count = 0
            last_time = now

# ──────────────────────────────────────────────────────────────────────────────
# MAIN PROGRAM ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start the debug panel thread (if enabled)
    if DEBUG_PANEL_ENABLED:
        threading.Thread(target=stats_ui, daemon=True).start()
    
    # Start the main scanner thread
    threading.Thread(target=scanner, daemon=True).start()
    
    # Keep the main thread alive
    while True:
        time.sleep(1)