# Oust
Also known as Candle Fight, Jonty Sebastian Joust, and "that game with the lights"

A love letter to [Johann Sebastian Joust](http://www.jsjoust.com/), designed for playing outdoors at noisy festivals in the dark. All night long (all night).

## How It Works
The aim of the game is to keep your orb lit by holding it steady. If you move it too fast, the light goes out and you lose.

Hold yours steady while trying to make other players move their orbs too fast. You could:

* Make them flinch.
* Hit their controller.
* Wait for them to do something silly.

The winner is the last person whose orb stays alight


![Rpi Oust Setup](sandwich_box.jpg)


## A long time ago on a boat far far away
When organising [Electromagnetic Wave](https://www.emfcamp.org/wave) in early 2013 we asked some of the [Wild Rumpus](http://thewildrumpus.co.uk/) organisers to run evening games on the boat. A very beta version of Joust was run on the deck to rave reviews.

Fast forward to 2015. We've taken Joust (in both beta and final versions) to [OHM](https://en.wikipedia.org/wiki/Observe._Hack._Make.) in 2013 and [EMF](https://www.emfcamp.org) in 2014. Every time the game runs all night with almost no supervision.

By this point the game has developed a bit of a following and people are actively seeking us out to play. But there are problems. Joust requires a laptop to run (meaning we need to be near a power supply and can't leave it alone), it needs speakers for the music (which we never have), and people have trouble understanding the gameplay without announcements and cues.

I went to [CCC](https://events.ccc.de/camp/2015/wiki/Main_Page) in 2015 prepared. We had 11 move controllers, three Raspberry Pis, 46 Ah of portable batteries, and more bluetooth adapters than there are bluetooth channels.

Oust is the result. It runs on a Raspberry Pi, can run up to 8 controllers (maybe more), and is specifically designed for environments so loud sign language is required.

It was playtested and tweaked extensively at CCC - at one point with a circle of approximately 150 people playing & watching. The longest game I recorded finished after 9 hours of continuous play.


## How to Oust
1. Turn the Raspberry Pi on.
2. Turn the controllers on.
3. Play!

## No really how does one Oust
The game is designed to run on a Raspberry Pi hooked up to a honking great battery pack. There is no interface other than the controllers themselves.

If you were starting out from scratch this is what it would look like:

1. Install Oust on the Raspberry Pi.
2. Plug the Pi into your battery pack.
3. Connect each controller to the Pi in turn using a MiniUSB cable. When the orb goes white it has been paired.
4. Turn on as many controllers as you want to play with.
5. Each player presses the trigger, and the game begins.
6. Optionally put the Pi & battery in a plastic sandwich box.


## What does the game look like?
1. All the controllers' orbs glow dark orange to show that they're connected.
1. Each player pulls the squishy trigger to join the game, and their controller lights up white to show they're ready to play.
1. When all the controllers are white (or when someone presses START) the controllers will vibrate, then flash red/yellow/green as a "get ready" signal.
1. Every controller turns a different colour and the game has begun.
1. The aim of the game is to force all the other players to move their controllers too fast, either by hitting the controller, making them flinch, or the other player doing something stupid.
1. If your controller is going too fast it'll flicker as a warning.
1. If you are knocked out, your controller goes dark and vibrates.
1. The last player standing is the winner! And their controller flashes a beautiful rainbow sequence, and all controllers vibrate to indicate the end of the game.
1. The game resets, people hand their controllers to other people to play. GOTO 1.

## Amazing Features
* Instant setup
* Easy pairing
* Add/remove controllers to/from the game on the fly
* Battery checking button (Press ⭕️ CIRCLE)
* Secret "goddamn it start the game" button (Press START)
* Turn off controller before the game starts (Press SELECT or PS)
* "Ready, Steady, Go" start sequence to get players attention
* Going-too-fast warning
* Support for as many controllers as bluetooth interference will allow

## Setup and Installation
### Essentials
* Raspberry Pi 3B
* MicroSD Card
* 4x PS3 Move Controller (1st generation) [🛍️ CEX](https://uk.webuy.com/product-detail/?id=SP3MCON001)
* 1+ Mini USB cable for pairing the PSMove controllers * 1x Micro USB cable for powering Raspberry Pi
* 1x USB Power Supply >=2.5A (12.5W+)

**Beware: The PSMove controllers will only charge over USB when connected to a USB Data Port!** They should however charge ok on a PSMove controller dock that uses the two metal contacts instead of USB.

### Install Software on Raspberry Pi

1. Install the operating system on an SD Card, using the official [Raspberry Pi Imager](https://www.raspberrypi.com/software/) with these settings:
	* **OS**: Other / Raspberry Pi OS Lite (64-bit)
	* **Hostname**: oust
	* **User**: oust/oust
	* **Wifi**: details to connect to your local network for setup
	* **SSH**: enabled
		* I chose to set this to *public-key only* and upload my public key, so password auth doesn't work over SSH

1. Boot Pi
1. SSH in `ssh oust@oust` or connect KVM to install stuff:

	```
	sudo apt update
	sudo apt install git vim bluez
	```
1. Install PSMove API
	1. Download Current PSMove API and install dependencies (took surprisingly long)

		```
		git clone https://github.com/thp/psmoveapi.git
		cd psmoveapi
		git submodule update --init
		bash -e -x scripts/install_dependencies.sh
		```
	1. Build PSMove API.
	
		```
		mkdir build
		cd build
		cmake .. -DPSMOVE_BUILD_TRACKER=OFF
		make
		```
		* If the above doesnt build you may need to do this first
			```
			bash -e -x scripts/linux/build-debian
			```
1. Change Bluetooth input settings to allow it to pair to PSMove controller.

	```
	echo -e "\n# Setting for PSMove to connect\nClassicBondedOnly=false" | sudo tee -a /etc/bluetooth/input.conf > /dev/null
	tail -n16 /etc/bluetooth/input.conf
	```
		
1. Install Oust

	```
	cd ~
	git clone https://github.com/MattGrayYes/Oust.git
	cd Oust	
	```
	
1. Check that Oust runs `sudo python oust.py`
	* Press `CTRL + C` to exit 
	* I recommend pairing a new controller at this point to test it all works with bluetooth.

1. Set up Oust in SystemD, so it auto-runs on boot. 
	1. Install the config file `sudo cp oust.service /etc/systemd/system/`
	1. Start the service: `sudo systemctl start oust.service`
	1. Monitor the service live as it runs `journalctl --follow --unit=oust.service --lines=20`
	1. Take a sneak peek at the service `systemctl status oust.service`
	1. If it all looks fine, enable the service `sudo systemctl enable oust.service`
	1. Reboot `sudo reboot`
	1. log back in and see if it's running `systemctl status oust.service`


Things You Should Know
----------------------
* The Playstation Move controllers actually implement the USB 1.2 standard, which means they NEED a data connection to charge. Essentially, you must connect them to a computer to charge them, a wall wart won't do.
