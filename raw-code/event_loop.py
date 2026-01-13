from __future__ import annotations

import threading
import time
from datetime import datetime
import sys

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction

from win11toast import toast

from custom_presence import EnhancedRPC, SpotifyRPC


def get_quick_timestamp() -> str:
    """quick and dirty func to get a simple timestamp for informational purposes"""
    return datetime.fromtimestamp(time.time()).strftime('%I:%M %p')


def presence_event_loop(stop_event: threading.Event):
    default_client = EnhancedRPC()
    spotify_client = SpotifyRPC()
    # Quick client connection startup
    print("\33[37mClients instantiated!")

    # The below is a terrible, hacky workaround for a silly Windows issue.
    while not stop_event.is_set():
        try:
            default_client.connect()
            default_client.update()
            print(f"\33[97mDefault client connected: {get_quick_timestamp()}")

            # infinite outer loop
            while True:
                # default client loop:
                while not spotify_client.is_playing:
                    default_client.update()
                    time.sleep(5)

                # for continuity, connect to new client before closing the previous one.
                spotify_client.connect()
                spotify_client.update()
                print(f"\33[97mSpotify client connected: {get_quick_timestamp()}")

                default_client.close()
                print(f"\033[93mDefault client disconnected: {get_quick_timestamp()}")

                while spotify_client.is_playing:
                    spotify_client.update()
                    time.sleep(5)

                print(f"\33[97mDefault client connected: {get_quick_timestamp()}")
                default_client.connect()
                default_client.update()

                print(f"\033[93mSpotify client disconnected: {get_quick_timestamp()}")
                spotify_client.close()

        except BrokenPipeError:
            pass

        except Exception as e:
            print(f"Warning: {e} ({get_quick_timestamp()})")

        try:
            default_client.close()
        except AssertionError:
            pass

        try:
            spotify_client.close()
        except AssertionError:
            pass


def tray_icon_application_builder(app: QApplication, stop_event: threading.Event):
    # Crucial: Keeps the app running even if the main window closes
    app.setQuitOnLastWindowClosed(False)

    # Icon for tray
    icon = QIcon("icon.png")

    # Create the tray
    tray = QSystemTrayIcon()
    tray.setIcon(icon)
    tray.setVisible(True)

    # Create the context menu
    menu = QMenu()
    exit_app = QAction("Close presence", menu)

    def on_exit():
        stop_event.set()
        app.quit()
        toast("DiscordRPC closed")

    exit_app.triggered.connect(on_exit)

    menu.addAction(exit_app)

    # Set the menu on the tray icon
    tray.setContextMenu(menu)

    return tray


def application_event_loop():
    stop_event = threading.Event()

    # Start your infinite loop in a background thread
    worker = threading.Thread(
        target=presence_event_loop,
        args=(stop_event,),
        daemon=True,          # daemon => app can exit even if loop is still running
        name="MainEventLoop"
    )
    worker.start()

    toast("DiscordRPC activated")

    # Start Qt tray on the MAIN thread
    app = QApplication(sys.argv)
    tray = tray_icon_application_builder(app, stop_event)

    exit_code = app.exec()

    # After Qt exits, request stop (in case user quits via other means)
    stop_event.set()

    # If you want to wait for a clean shutdown, you can join briefly:
    worker.join(timeout=2.0)

    sys.exit(exit_code)
