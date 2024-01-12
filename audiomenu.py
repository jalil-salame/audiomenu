import shutil
import shlex
from dataclasses import dataclass
from enum import Enum
from json import loads
from subprocess import run, CalledProcessError
from typing import Any

import click

Direction = Enum("Direction", ["INPUT", "OUTPUT"])


@dataclass(slots=True)
class AudioDevice:
    id: int
    name: str
    direction: Direction
    muted: bool | None = None
    volume: float | None = None

    def fetch_volume(self) -> None:
        if self.volume is not None and self.muted is not None:
            return

        output = run(
            ["wpctl", "get-volume", str(self.id)],
            capture_output=True,
            check=True,
            encoding="UTF-8",
        )

        match output.stdout.removeprefix("Volume: ").split(" "):
            case [volume]:
                self.muted = False
                self.volume = float(volume)
            case [volume, mute]:
                assert mute == "[MUTED]"
                self.muted = True
                self.volume = float(volume)
            case volume_expr:
                raise ValueError(f"unexpected: {volume_expr=}")


def audio_device_from_pw_node(node: dict[str, Any]) -> AudioDevice | None:
    try:
        if node["type"] != "PipeWire:Interface:Node":
            return None  # Not a device
        props = node["info"]["props"]

        id = props["object.id"]
        name = props["node.description"]
        direction = Direction.INPUT

        match props["media.class"]:
            case "Audio/Sink":
                direction = Direction.OUTPUT
            case "Audio/Source":
                direction = Direction.INPUT
            case _:
                return None

        return AudioDevice(id=id, name=name, direction=direction)
    except KeyError:
        # Malformed data
        return None


def get_audio_devices() -> list[AudioDevice]:
    output = run(["pw-dump"], capture_output=True, check=True)
    dump: list[dict[str, Any]] = loads(output.stdout)
    parse_dev = audio_device_from_pw_node
    return [dev for node in dump if (dev := parse_dev(node)) is not None]


def get_inputs() -> list[AudioDevice]:
    def is_input(dev: AudioDevice) -> bool:
        return dev.direction == Direction.INPUT

    return [dev for dev in get_audio_devices() if is_input(dev)]


def get_outputs() -> list[AudioDevice]:
    def is_output(dev: AudioDevice) -> bool:
        return dev.direction == Direction.OUTPUT

    return [dev for dev in get_audio_devices() if is_output(dev)]


def populate_volume(devices: list[AudioDevice]) -> None:
    for dev in devices:
        dev.fetch_volume()


def find_menuprog() -> str | None:
    for prog in ["dmenu", "dmenu-wl", "rofi -dmenu", "fuzzel --dmenu"]:
        if shutil.which(prog.split(" ")[0]) is not None:
            return prog


@click.group()
@click.option("--menu", default=find_menuprog, show_default=True)
@click.pass_context
def audiomenu(ctx, menu: str | None) -> None:
    """
    dmenu script to select the default audio device for pipewire+wireplumber
    """
    if menu is None:
        raise click.UsageError("couldn't find an appropiate menu program")

    ctx.obj["MENUPROG"] = shlex.split(menu)


@audiomenu.command()
@click.pass_context
def select_source(ctx) -> None:
    """
    Select audio source (microphone)
    """
    menu = ctx.obj["MENUPROG"]

    try:
        sources = "\n".join((f"{dev.id} {dev.name}" for dev in get_inputs()))
        output = run(
            menu,
            input=sources,
            capture_output=True,
            encoding="UTF-8",
            check=True,
        )

        id = output.stdout.split(" ")[0]
        run(["wpctl", "set-default", id], check=True)
    except CalledProcessError:
        pass


@audiomenu.command()
@click.pass_context
def select_sink(ctx) -> None:
    """
    Select audio sink (speakers/headphones)
    """
    menu = ctx.obj["MENUPROG"]

    sources = "\n".join((f"{dev.id} {dev.name}" for dev in get_outputs()))
    try:
        output = run(
            menu,
            input=sources,
            capture_output=True,
            encoding="UTF-8",
            check=True,
        )

        id = output.stdout.split(" ")[0]
        run(["wpctl", "set-default", id], check=True)
    except CalledProcessError:
        pass


if __name__ == "__main__":
    audiomenu(obj={})
