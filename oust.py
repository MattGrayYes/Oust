from __future__ import print_function
import os
import sys
import time

# warn if not running as root
if os.geteuid() != 0:
    print("ERROR: You need to run Oust as root so it has Bluetooth access.")   
    exit(1)

BASE = os.path.join(os.path.dirname(__file__), '..', 'psmoveapi')

if 'PSMOVEAPI_LIBRARY_PATH' not in os.environ:
    os.environ['PSMOVEAPI_LIBRARY_PATH'] = os.path.join(BASE, 'build')

sys.path.insert(0, os.path.join(BASE, 'bindings', 'python'))

import psmoveapi

import subprocess
from collections import defaultdict

# Track all controller objects by serial number for access during animations
_controller_registry = {}

def disconnect_move_by_serial(serial):
    subprocess.call(['hcitool', 'dc', serial])

def pair_controllers():
    """Run the psmove pair utility to pair USB-connected controllers"""
    library_path = os.environ.get('PSMOVEAPI_LIBRARY_PATH', os.path.join(os.path.dirname(__file__), '..', 'psmoveapi', 'build'))
    pair_binary = os.path.join(library_path, 'psmove')
    
    if not os.path.exists(pair_binary):
        print(f"Warning: psmove binary not found at {pair_binary}")
        return False
    
    print(f"Running pairing utility: {pair_binary} pair")
    try:
        # Run the pairing command - note this needs sudo privileges
        result = subprocess.run(['sudo', pair_binary, 'pair'], 
                              capture_output=True, 
                              text=True,
                              timeout=10)
        
        # Print all output (both stdout and stderr)
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='')
        
        # Check if pairing succeeded by looking for success message in output
        success = 'succeeded' in result.stdout.lower() or 'succeeded' in result.stderr.lower()
        
        if success:
            print("Pairing succeeded! Unplug USB and press PS button to connect via Bluetooth")
        
        return success
    except subprocess.TimeoutExpired:
        print("Pairing command timed out")
        return False
    except Exception as e:
        print(f"Error running pairing command: {e}")
        return False

# This nightmarish function was taken from stackoverflow
def hsv_to_rgb(h, s, v):
    if s == 0.0: v*=255; return [v, v, v]
    i = int(h*6.)
    f = (h*6.)-i; p,q,t = int(255*(v*(1.-s))), int(255*(v*(1.-s*f))), int(255*(v*(1.-s*(1.-f)))); v*=255; i%=6
    if i == 0: return [v, t, p]
    if i == 1: return [q, v, p]
    if i == 2: return [p, v, t]
    if i == 3: return [p, q, v]
    if i == 4: return [t, p, v]
    if i == 5: return [v, p, q]


class OustGame(psmoveapi.PSMoveAPI):
    def __init__(self):
        super().__init__()
        self.quit = False
        
        # Game state
        self.paired_controllers = []
        self.usb_paired_controllers = []
        self.controllers_alive = {}
        self.controller_colours = {}
        self.poll_failures = defaultdict(int)
        
        # Game flags
        self.in_lobby = True
        self.in_game = False
        self.in_countdown = False
        self.battery_mode = False
        self.start_pressed = False
        
        # Game data
        self.move_last_values = {}
        
    def on_connect(self, controller):
        print(f"Controller {controller.serial} connected")
        
        # If a controller is plugged in over USB, automatically run pairing
        if controller.usb:
            if controller.serial not in self.usb_paired_controllers:
                self.usb_paired_controllers.append(controller.serial)
                print(f"{controller.serial} connected over USB - attempting to pair...")
                controller.color = psmoveapi.RGB(1.0, 1.0, 1.0)
                
                # Automatically run the pairing utility
                pair_controllers()
        
        # If the controller connects over BT, add it to the list and turn it white
        elif controller.bluetooth:
            if controller.serial not in self.paired_controllers:
                self.paired_controllers.append(controller.serial)
                print(f"{controller.serial} connected over bluetooth")
                controller.color = psmoveapi.RGB(1.0, 1.0, 1.0)
    
    def on_update(self, controller):
        # Skip USB controllers (they're just for pairing)
        if controller.usb:
            controller.color = psmoveapi.RGB(1.0, 1.0, 1.0)
            return

        if self.in_lobby:
            self.handle_lobby_update(controller)
        elif self.in_countdown:
            return
        elif self.in_game:
            self.handle_game_update(controller)
    
    def on_disconnect(self, controller):
        print(f"Controller {controller.serial} disconnected")
        if controller.serial in self.controllers_alive:
            del self.controllers_alive[controller.serial]
        if controller.serial in self.move_last_values:
            del self.move_last_values[controller.serial]
    
    def handle_lobby_update(self, controller):        
        # If the trigger is pulled, join the game
        if controller.serial not in self.controllers_alive:
            if controller.trigger > 0.5:  # Trigger is 0.0-1.0, so > 0.5 means pulled halfway
                self.controllers_alive[controller.serial] = controller
                print(f"{controller.serial} joined the game")
        
        # Set LED based on whether they're in the game
        if controller.serial in self.controllers_alive:
            controller.color = psmoveapi.RGB(1.0, 1.0, 1.0)
        else:
            controller.color = psmoveapi.RGB(0.2, 0.1, 0.0)
        
        # START starts the game early (button value 2048 = START)
        if controller.buttons & (1 << 11):  # START button
            self.start_pressed = True
        
        # Circle shows battery level (button value 32 = CIRCLE)
        if controller.buttons & (1 << 5):  # CIRCLE button
            self.battery_mode = True
            level = controller.battery
            
            if level == 5:  # 100% - green
                controller.color = psmoveapi.RGB(0.0, 1.0, 0.0)
            elif level == 4:  # 80% - green-ish
                controller.color = psmoveapi.RGB(0.5, 0.78, 0.0)
            elif level == 3:  # 60% - yellow
                controller.color = psmoveapi.RGB(1.0, 1.0, 0.0)
            else:  # <= 40% - red
                controller.color = psmoveapi.RGB(1.0, 0.0, 0.0)
        else:
            if self.battery_mode:
                self.battery_mode = False
        
        controller.rumble = 0
        
        # SELECT or PS disconnects the controller
        if controller.buttons & (1 << 8) or controller.buttons & (1 << 16):  # SELECT or PS button
            disconnect_move_by_serial(controller.serial)
    
    def handle_game_update(self, controller):
        # Only process controllers that are alive in the game
        if controller.serial not in self.controllers_alive:
            controller.color = psmoveapi.RGB(0.0, 0.0, 0.0)
            return
        
        # Get accelerometer data
        ax = controller.accelerometer.x
        ay = controller.accelerometer.y
        az = controller.accelerometer.z
        total = abs(ax) + abs(ay) + abs(az)
        
        if controller.serial in self.move_last_values:
            change = abs(self.move_last_values[controller.serial] - total)
            
            # Dead
            if change > 0.7:
                print(f"DEAD {controller.serial}")
                controller.color = psmoveapi.RGB(0.0, 0.0, 0.0)
                controller.rumble = 100
                del self.controllers_alive[controller.serial]
            
            # Warn
            elif change > 0.2:
                r, g, b = self.controller_colours[controller.serial]
                controller.color = psmoveapi.RGB(r*0.3/255.0, g*0.3/255.0, b*0.3/255.0)
            
            # Reset
            else:
                r, g, b = self.controller_colours[controller.serial]
                controller.color = psmoveapi.RGB(r/255.0, g/255.0, b/255.0)
                controller.rumble = 0
        
        self.move_last_values[controller.serial] = total
    
    def regenerate_colours(self):
        """Generate unique colors for each controller in the game"""
        alive_serials = list(self.controllers_alive.keys())
        HSV = [(x*1.0/len(alive_serials), 1, 1) for x in range(len(alive_serials))]
        colour_range = [[int(x) for x in hsv_to_rgb(*colour)] for colour in HSV]
        self.controller_colours = {serial: colour_range[i] for i, serial in enumerate(alive_serials)}
    
    def sleep_controllers(self, sleep_time, leds, rumble):
        """Sleep while keeping all alive controllers at specific LED/rumble settings"""
        pause_time = time.time() + sleep_time
        while time.time() < pause_time:
            for serial, controller in self.controllers_alive.items():
                controller.color = psmoveapi.RGB(leds[0], leds[1], leds[2])
                controller.rumble = rumble
            self.update()  # Actually send the color/rumble updates to hardware
            time.sleep(0.01)
    
    def check_game_start_conditions(self):
        """Check if we should start the game"""
        num_alive = len(self.controllers_alive)
        
        # Everyone's in
        if num_alive >= 2 and num_alive == len(self.paired_controllers):
            return True
        
        # Someone hit START
        if num_alive >= 2 and self.start_pressed:
            return True
        
        return False
    
    def start_game(self):
        """Transition from lobby to game"""
        print("Game Starting")
        self.in_lobby = False
        self.in_countdown = True
        self.start_pressed = False
        
        # Generate colors for each player
        print("Generating Colours")
        self.regenerate_colours()
        
        # Countdown sequence
        print("Countdown Sequence")

        # White
        self.sleep_controllers(0.5, (1.0, 1.0, 1.0), 0)
        # White/rumble
        self.sleep_controllers(0.3, (1.0, 1.0, 1.0), 100)
        # Red/no rumble
        self.sleep_controllers(0.75, (0.2, 0, 0), 0)
        # Yellow
        self.sleep_controllers(0.75, (0.2, 0.3, 0), 0)
        # Green
        self.sleep_controllers(0.75, (0, 0.2, 0), 0)
        
        # Set individual colours
        for serial, controller in self.controllers_alive.items():
            r, g, b = self.controller_colours[serial]
            controller.color = psmoveapi.RGB(r/255.0, g/255.0, b/255.0)
        
        self.in_countdown = False
        self.in_game = True
        print("Game Start!")

    
    def check_game_end_conditions(self):
        """Check if the game should end"""
        if len(self.controllers_alive) <= 1:
            return True
        return False
    
    def end_game(self):
        """Handle game end and winner celebration"""
        if len(self.controllers_alive) == 1:
            winner_serial = list(self.controllers_alive.keys())[0]
            winner = self.controllers_alive[winner_serial]
            print(f"WIN {winner_serial}")
            
            # Create rainbow animation
            HSV = [(x*1.0/50, 0.9, 1) for x in range(50)]
            colour_range = [[int(x) for x in hsv_to_rgb(*colour)] for colour in HSV]
            
            pause_time = time.time() + 3
            idx = 0
            while time.time() < pause_time:
                # Winner gets rainbow
                r, g, b = colour_range[idx % len(colour_range)]
                winner.color = psmoveapi.RGB(r/255.0, g/255.0, b/255.0)
                winner.rumble = 100
                self.update()  # Send the color/rumble updates to hardware
                idx += 1
                time.sleep(0.01)
        
        # Reset game state
        self.in_game = False
        self.in_countdown = False
        self.in_lobby = True
        self.controllers_alive = {}
        self.move_last_values = {}
        self.controller_colours = {}
    
    def run(self):
        """Main game loop"""
        while not self.quit:
            self.update()
            
            # Check lobby conditions
            if self.in_lobby and self.check_game_start_conditions():
                self.start_game()
            
            # Check game end conditions
            if self.in_game and self.check_game_end_conditions():
                self.end_game()
            
            time.sleep(0.01)


if __name__ == '__main__':
    print("=" * 6)
    print(" OUST ")
    print("=" * 6)
    print("This game is designed to work unattended with no screen")
    print("=" * 60)
    print("\n* Pairing a new controller *")
    print("1. Plug in PS Move controller via USB")
    print("2. Wait for light to turn solid white")
    print("3. Unplug USB cable")
    print("4. Press the PS button on the controller to connect via Bluetooth")
    print("5. Controller lights up dim orange to show it's connected")
    print("\n* Button Controls: *")
    print("While in the lobby:")
    print(" - Pull trigger to join the game")
    print(" - Press CIRCLE to show battery level")
    print(" - Press SELECT to disconnect controller")
    print(" - Press START to start the game early\n")


    # Unblock bluetooth
    try:
        print("Unblocking bluetooth using rfkill...")
        subprocess.run(['sudo', 'rfkill', 'unblock', 'bluetooth'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to unblock bluetooth: {e}")
    except FileNotFoundError:
        print("Warning: rfkill command not found")

    print("Let's go!\n")
    
    game = OustGame()
    game.run()

