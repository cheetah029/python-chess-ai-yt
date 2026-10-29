# Game Instructions

* Working on AI gamemode...

- Entry point: main.py
- Press 't' to change theme (green, brown, blue, gray)
- Press 'r' to restart the game

# Player versions

Every distinct version of the computer player is kept, including
versions that were never committed (a window launched mid-edit). The
window's title bar shows the id of the player it is running, and the
window saves that version when it starts. To list them or play one
again:

```bash
python src/player_versions.py list
```

```bash
python src/player_versions.py play <id>
```

`play` unpacks the version under `~/.cache/royal-chess-players/` and
runs it there; the checkout is not touched. Versions live in this
repository under `refs/players/`.

# Game Snapshots

## Snapshot 1 - Start (green)
![snapshot1](snapshots/snapshot1.png)

## Snapshot 2 - Start (brown)
![snapshot2](snapshots/snapshot2.png)

## Snapshot 3 - Start (blue)
![snapshot3](snapshots/snapshot3.png)

## Snapshot 4 - Start (gray)
![snapshot4](snapshots/snapshot4.png)

## Snapshot 5 - Valid Moves
![snapshot5](snapshots/snapshot5.png)

## Snapshot 6 - Castling
![snapshot6](snapshots/snapshot6.png)
