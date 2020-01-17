# robosses

a 2D Boss Rush Platformer written in Python using the Pygame library for the [GameShell Game Jam (2019Q4)](https://itch.io/jam/gameshell-19q4).

![Octopus](https://user-images.githubusercontent.com/43303199/72630512-1dca0a80-3918-11ea-8083-110deda1eb0d.gif)

## Background

*Robosses* was designed to run natively on the ClockworkPi GameShell, but you can run the game on any computer that has the latest version of Python and Pygame installed.

## ClockworkPi GameShell Installation Methods

### Installation via Warehouse (GameShell OS v0.5)

*Robosses*, and all of our other GameShell supported games, can be downloaded easily via the new Warehouse feature introduced in GameShell OS v0.5. Outlined below are the exact steps you must follow to install *Robosses* using the Warehouse feature.

1. Open the Warehouse application on your GameShell.

2. Click on the "Add new warehouse..." button.

3. Enter `github.com/thismarvin/warehouse` as the Warehouse address.

4. A new Warehouse should appear in the Warehouse menu, and all of our games can be previewed and installed by navigating inside that Warehouse!

### Installation via Terminal

To install *Robosses* using the terminal you must ssh into your GameShell from your desktop or laptop and clone this repository. Before doing so make sure that your desktop or laptop is on the same network as the GameShell. Outlined below are the exact steps you must follow to install *Robosses* using the terminal.

1. SSH into your GameShell from your computer's terminal. Your GameShell's IPv4 Address can be found in the Tiny Cloud application.

    ```bash
    ssh cpi@192.168.0.0
    ```

2. Clone this repository onto your GameShell.

    ``` bash
    git clone https://github.com/thismarvin/robosses.git /home/cpi/games/Python/robosses
    ```

3. Create a launcher for *Robosses* in the "Indie Games" folder.

    ```bash
    mv /home/cpi/games/Python/robosses/33_Robosses/ /home/cpi/apps/Menu/21_Indie\ Games/
    ```

4. Reload the UI on your GameShell, and enjoy playing *Robosses*!
