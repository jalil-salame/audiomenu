# Audiomenu

A dmenu script to select the default audio source/sink in pipewire+wireplumber

## Usage

Map a key to `audiomenu select-source` and `audiomenu select-sink`

You can set the dmenu program with `--menu 'fuzzel --dmenu'`. By default it
will use the first available from `dmenu`, `dmenu-wl`, `rofi`, `fuzzel` and `wofi`.

## Building

Build with nix flakes:

```console
$ nix build
```
