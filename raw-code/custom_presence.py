from __future__ import annotations

import os
import requests
import time
import json
from datetime import datetime, UTC
from pypresence import Presence
from spotipy import Spotify, SpotifyOAuth


# current_config setup— based on current_config.json
with open("config.json", "r") as config:
    config_info = json.load(config)

# Spotify API client information
os.environ['SPOTIPY_CLIENT_ID'] = config_info["spotify_api"]["client_id"]
os.environ['SPOTIPY_CLIENT_SECRET'] = config_info["spotify_api"]["client_secret"]
os.environ['SPOTIPY_REDIRECT_URI'] = config_info["spotify_api"]["redirect_uri"]

# API keys, client IDs
WEATHER_API_KEY = config_info["general_api_keys"]["weather_api_key"]
DEFAULT_RPC_ID = config_info["general_api_keys"]["default_rpc_id"]
SPOTIFY_RPC_ID = config_info["general_api_keys"]["spotify_rpc_id"]

# metadata— including image list
DEFAULT_IMAGE_LIST = config_info["metadata"]["default_image_list"]
SPOTIFY_IMAGE_LIST = config_info["metadata"]["spotify_image_list"]
CURRENT_CITY = config_info["metadata"]["city"]

LAST_WEATHER_UPDATE = -1
CURRENT_WEATHER_CONDITION = None


# Local helper functions
def get_date_time(curr_time: int = -1, leading: bool = True, military_time: bool = False) -> dict[
        str, dict[str, str | None] | dict[str, str] | dict[str, int]]:
    """Returns current date and time in the style of HH:MM:AM/PM.
    Takes time in epoch, with current time as default if none given.

    Takes leading bool for whether leading zeros should be included or not.
    Takes military_time bool for 24hr/12hr time.
    """
    curr_time = time.time() if curr_time < 0 else curr_time
    time_obj = datetime.fromtimestamp(curr_time)

    # Time in day
    hour = time_obj.strftime('%I') if not military_time else time_obj.strftime('%H')
    if not leading:
        hour = hour.lstrip('0')
    minute = time_obj.strftime('%M')
    am_pm = None if military_time else time_obj.strftime('%p')

    # Day in year
    weekday = time_obj.strftime("%A")
    day = time_obj.strftime("%d")
    month = time_obj.strftime("%B")
    year = time_obj.strftime("%Y")

    # Metadata
    time_zone = datetime.fromtimestamp(3138004800).hour - datetime.fromtimestamp(3138004800, UTC).hour

    # Hotfix to ensure that all timezones East of GMT have an additional "+" to
    # follow general convention.
    if time_zone >= 0:
        time_zone = f"+{time_zone}"

    # This is to ensure that the time_zone variable keeps one consistent type.
    time_zone = str(time_zone)

    # Formatting dict
    time_dict = {
        "exact": {
            "hour": hour,
            "minute": minute,
            "am_pm": am_pm
        },
        "broad": {
            "weekday": weekday,
            "day": day,
            "month": month,
            "year": year
        },
        "meta": {
            "timezone": time_zone
        }
    }

    return time_dict


def get_current_weather(city: str) -> dict | None:
    """Helper function to access the openweathermap API and retrieve local
    weather data.

    Choose your city as a parameter.
    Returns a dictionary with important outputs.
    """

    global LAST_WEATHER_UPDATE, CURRENT_WEATHER_CONDITION

    if not round(time.time()) - LAST_WEATHER_UPDATE > 1800:
        return CURRENT_WEATHER_CONDITION

    #  ̶T̶h̶i̶s̶ ̶i̶s̶ ̶E̶X̶T̶R̶E̶M̶E̶L̶Y̶ ̶p̶o̶o̶r̶ ̶p̶r̶a̶c̶t̶i̶c̶e̶.̶ ̶R̶e̶m̶e̶m̶b̶e̶r̶ ̶t̶o̶ ̶r̶e̶m̶o̶v̶e̶ ̶i̶n̶ ̶t̶h̶e̶ ̶f̶u̶t̶u̶r̶e̶!̶
    # The issue has been resolved using global values!
    _key = WEATHER_API_KEY
    response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q="
                            f"{city}&appid={_key}&units=metric").json()

    weather_data = {
        "temp": {
            "feels_like": response["main"]["feels_like"],
            "temp_min": response["main"]["temp_min"],
            "temp_nax": response["main"]["temp_max"],
            "temp": response["main"]["temp"]
        },
        "weather": {
            "description": response["weather"][0]["description"],
            "main": response["weather"][0]["main"]
        },
        "meta": {
            "city": response["name"],
            "country": response["sys"]["country"]
        }
    }

    CURRENT_WEATHER_CONDITION = weather_data
    LAST_WEATHER_UPDATE = round(time.time())

    return weather_data


def get_ordinal_suffix(num: int) -> str:
    """Helper function to return a suffix for any numeral. In other words,
    it returns '-st', '-nd', '-rd', and '-th' for any numeric input."""

    # General exception edge cases- 11, 12, 13
    if num in [11, 12, 13]:
        return 'th'

    # Generic values
    last_digit = num % 10

    match last_digit:
        case 1:
            return 'st'

        case 2:
            return 'nd'

        case 3:
            return 'rd'

    # Final general catch-all
    return 'th'


class EnhancedRPC(Presence):
    """A Discord RPC Presence Object, specifically for use with default weather
    and time information built in.
    """

    DEFAULT_ID = DEFAULT_RPC_ID
    client_id: int
    image_num: int

    client_start: int
    current_state: dict[str, str | None]

    def __init__(self, client_id: int = -1) -> None:
        """Creates a new Presence object. Takes some defaults."""
        self.client_id = EnhancedRPC.DEFAULT_ID if client_id == -1 else client_id
        self.image_num = 0

        # Get first start time
        self.client_start = int(time.time())

        self.current_state = {
            "state": None,
            "details": None,
            "large_text": None,
            "small_image": None,
            "small_text": None,
            "buttons": None
        }

        super().__init__(self.client_id)

    def update(self, pid: int = os.getpid(),
               state: str = None, details: str = None,
               start: int = None, end: int = None,
               large_image: str = None, large_text: str = None,
               small_image: str = None, small_text: str = None,
               party_id: str = None, party_size: list = None,
               join: str = None, spectate: str = None,
               match: str = None, buttons: list = None,
               instance: bool = True, payload_override: dict = None):
        """Override of default update behaviour using time and weather.
        If any of the parameters are filled, they will override the default
        parameter."""
        if state is None and details is None:
            state, details = EnhancedRPC.tooltip_helper()

        if large_image is None:
            large_image = self._cycle_image

        if start is None:
            start = self.client_start

        if large_text is None:
            broad_time = get_date_time()["broad"]
            large_text = f"{broad_time["weekday"]}, {broad_time["month"]} {broad_time["day"].lstrip('0') +
                                                                           get_ordinal_suffix(int(broad_time["day"]))}"

        previous_state = self.current_state.copy()

        # dump contents to current_config
        self.current_state = {
            "state": state,
            "details": details,
            "large_text": large_text,
            "small_image": small_image,
            "small_text": small_text,
            "buttons": buttons
        }

        if self.needs_update(previous_state):
            return super().update(pid, state, details, start, end, large_image,
                                  large_text, small_image, small_text, party_id,
                                  party_size, join, spectate, match, buttons,
                                  instance, payload_override)

        return

    @staticmethod
    def tooltip_helper() -> tuple[str, str]:
        """Returns the default state/detail pairing for default presence update.
        This specific implementation returns current time and weather.

        Friendly reminder: Details are displayed ABOVE the state.
        """

        current_time = get_date_time()["exact"]
        state = (f"It is {current_time["hour"].lstrip("0")}:{current_time["minute"]} {current_time["am_pm"]} "
                 f"(UTC {get_date_time()["meta"]["timezone"]})")

        current_weather = get_current_weather(CURRENT_CITY)
        details = (f"{round(current_weather["temp"]["temp"])}°C, "
                   f"{' '.join(word.capitalize() for word in current_weather["weather"]["description"].split(' '))}")

        return state, details

    @property
    def _cycle_image(self) -> str:
        """Cycles linearly through the images, and returns the next one."""

        #  ̶T̶h̶i̶s̶ ̶s̶h̶o̶u̶l̶d̶ ̶b̶e̶ ̶c̶h̶a̶n̶g̶e̶d̶ ̶f̶o̶r̶ ̶a̶ ̶g̶e̶n̶e̶r̶a̶l̶ ̶s̶o̶l̶u̶t̶i̶o̶n̶ ̶s̶o̶m̶e̶ ̶t̶i̶m̶e̶ ̶i̶n̶ ̶t̶h̶e̶ ̶f̶u̶t̶u̶r̶e̶
        # General solution found and replaced!
        images = DEFAULT_IMAGE_LIST

        # Creates a copy of the current index, then iterates the value by 1
        current_index = int(self.image_num)
        self.image_num = self.image_num + 1 if self.image_num < len(images) - 1 else 0

        return images[current_index]

    def needs_update(self, current_config: dict) -> bool:
        """Returns true iff the current state of the RPC is different from the
        state offered in the current_config.

        If a value in current_config is left as NoneType, its comparison will be
        ignored.
        """

        for key in current_config:
            if current_config[key] is not None:
                if current_config[key] != self.current_state[key]:
                    return True

        return False


class SpotifyRPC(Presence):
    """A Discord RPC Presence Object, specifically for use with the Spotify API
    and displays the current music playing.
    """

    DEFAULT_ID = SPOTIFY_RPC_ID
    DEFAULT_SMALL_PLAYING_ICON = "spotify_playing"

    client_id: int
    image_num: int
    spotify_client: Spotify
    values: dict | None

    current_state: dict[str, str | int | None]

    def __init__(self, client_id: int = -1) -> None:
        """Creates a new Presence object. Takes some defaults."""
        self.client_id = SpotifyRPC.DEFAULT_ID if client_id == -1 else client_id
        self.image_num = 0
        self.spotify_client = Spotify(auth_manager=SpotifyOAuth(scope="user-read-currently-playing"))
        self.values = None

        self.current_state = {
            "state": None,
            "details": None,
            "large_text": None,
            "small_image": None,
            "small_text": None,
            "buttons": None
        }

        super().__init__(self.client_id)

    def update(self, pid: int = os.getpid(),
               state: str = None, details: str = None,
               start: int = None, end: int = None,
               large_image: str = None, large_text: str = None,
               small_image: str = None, small_text: str = None,
               party_id: str = None, party_size: list = None,
               join: str = None, spectate: str = None,
               match: str = None, buttons: list = None,
               instance: bool = True, payload_override: dict = None):
        """Override of default update behaviour using time and weather.
        If any of the parameters are filled, they will override the default
        parameter."""

        try:
            default_values = self.currently_playing_helper()
        except TypeError:
            time.sleep(5)
            default_values = self.currently_playing_helper()

        if default_values is None:
            return

        if state is None and details is None:
            state, details = default_values["state"], default_values["details"]

        if large_image is None:
            large_image = self._cycle_image

        if small_image is None:
            small_image = SpotifyRPC.DEFAULT_SMALL_PLAYING_ICON

        if start is None:
            start = default_values["start"]

        if buttons is None:
            buttons = default_values["buttons"]

        if large_text is None and small_text is None:
            current_time = get_date_time()["exact"]
            small_text = (f"It is {current_time["hour"].lstrip("0")}:{current_time["minute"]} {current_time["am_pm"]} "
                          f"(UTC {get_date_time()["meta"]["timezone"]})")

            current_weather = get_current_weather(CURRENT_CITY)
            large_text = (f"{round(current_weather["temp"]["temp"])}°C, "
                          f"{' '.join(word.capitalize() for word in current_weather["weather"]
                                                                                   ["description"].split(' '))}")

        previous_state = self.current_state.copy()

        # dump contents to current_config
        self.current_state = {
            "state": state,
            "details": details,
            "large_text": large_text,
            "small_image": small_image,
            "small_text": small_text,
            "buttons": buttons
        }

        if self.needs_update(previous_state):
            return super().update(pid, state, details, start, end, large_image,
                                  large_text, small_image, small_text, party_id,
                                  party_size, join, spectate, match, buttons,
                                  instance, payload_override)

        return

    def currently_playing_helper(self) -> dict[str, str | list[dict]] | None:
        """Returns currently playing song and artist, using the Spotify API.
        Friendly reminder: Details are displayed ABOVE the state.
        """

        try:
            results = self.values.copy()
            state = f"by {', '.join([artist['name'] for artist in results['item']['artists']])}"
            details = f"{results['item']['name']}"

        except TypeError:
            # Perhaps could be the result of the player not working—
            # Just return for now. Check for whether the player is still running
            return None

        # buttons
        button = [{"label": "Play on Spotify", "url": f"spotify://track/{results['item']['id']}"}]

        # start time
        start = round(time.time() - results['progress_ms'] / 1000)

        output_config = {
            "state": state,
            "details": details,
            "start": start,
            "buttons": button
        }

        return output_config

    @property
    def _cycle_image(self) -> str:
        """Cycles linearly through the images, and returns the next one."""

        #  ̶T̶h̶i̶s̶ ̶s̶h̶o̶u̶l̶d̶ ̶b̶e̶ ̶c̶h̶a̶n̶g̶e̶d̶ ̶f̶o̶r̶ ̶a̶ ̶g̶e̶n̶e̶r̶a̶l̶ ̶s̶o̶l̶u̶t̶i̶o̶n̶ ̶s̶o̶m̶e̶ ̶t̶i̶m̶e̶ ̶i̶n̶ ̶t̶h̶e̶ ̶f̶u̶t̶u̶r̶e̶
        # General solution found and replaced!
        images = SPOTIFY_IMAGE_LIST

        # Creates a copy of the current index, then iterates the value by 1
        current_index = int(self.image_num)
        self.image_num = self.image_num + 1 if self.image_num < len(images) - 1 else 0

        return images[current_index]

    @property
    def is_playing(self) -> bool:
        """Return whether the Spotify client is running, and is actively playing
        a song."""

        # check for whether the client is playing music
        # Set the market as CA to reduce the amount of data transferred
        # Also useful for debugging purposes!
        self.values = self.spotify_client.currently_playing(market="CA")

        try:
            if "is_playing" in self.values:
                return self.values["is_playing"]
        except TypeError:
            pass

        return False

    def needs_update(self, current_config: dict) -> bool:
        """Returns true iff the current state of the RPC is different from the
        state offered in the current_config.

        If a value in current_config is left as NoneType, its comparison will be
        ignored.

        In this version, the "start" value is treated DIFFERENTLY with a 5-
        second error given to prevent discrepancies in pipeline.
        """

        for key in current_config:
            if current_config[key] is not None:

                if key == "start" and abs(self.current_state[key] - current_config[key]) > 5:
                    return True

                elif current_config[key] != self.current_state[key]:
                    return True

        return False


if __name__ == "__main__":
    default_presence = EnhancedRPC()
    default_presence.close()
