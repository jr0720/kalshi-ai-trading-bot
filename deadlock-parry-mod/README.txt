PARRY! Heavy Melee Voice Line — Deadlock sound mod
==================================================

Replaces the charged (heavy) melee swing sound with a loud "PARRY!"
voice line. Because sound mods are client-side, you will hear it for
YOUR heavy melees AND for enemies'/teammates' — an enemy winding up a
heavy melee near you will effectively yell PARRY at you, positionally.
Nobody else in the match hears anything.

Replaced files:
  sounds/player/melee/shared/charged_melee_full.vsnd_c   (windup/charge - the main heavy melee sound, shared by ALL heroes)
  sounds/player/melee/shared/swing_charged_01..07.vsnd_c (swing whoosh on release)

INSTALL — Deadlock Mod Manager:
  Add this .vpk as a local mod (or drop the zip in), then launch the game
  through the manager as usual.

INSTALL — manual:
  Copy pak97_dir.vpk into:
    .../steamapps/common/Deadlock/game/citadel/addons/
  (Create the folder if needed. You must have mods enabled once via the
  Mod Manager or a gameinfo.gi search-path edit for addons to load.)

USE YOUR OWN VOICE:
  Record yourself shouting "PARRY!" (about half a second), save as WAV
  or MP3, then run:
    python3 make_parry_vpk.py your_recording.wav
  Requires Python 3 and ffmpeg on PATH. It rebuilds pak97_dir.vpk with
  your voice, loudness-maximized, and packs it automatically.

UNINSTALL: delete pak97_dir.vpk from the addons folder / disable in the
Mod Manager.

Game updates occasionally break sound mods; if the sound reverts after a
patch, just re-install (or rebuild) the vpk.

TROUBLESHOOTING - "I hear no change in game":
  1. Make sure the vpk is really in game/citadel/addons/ after enabling.
  2. Mods must be enabled once: in Deadlock Mod Manager run its setup so it
     patches gameinfo.gi. Steam's "Verify integrity of game files" UNDOES
     this patch - re-run the manager's setup after verifying/updating.
  3. Quick mount test: install any known-working sound mod from GameBanana
     via the manager. If that also changes nothing, addons aren't mounting
     (see step 2). If it works but this one doesn't, report it.
