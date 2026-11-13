# oneshot-horizon-data

Data packs for the OneShot Android build of Horizon
([oneshot-horizon-builds](https://github.com/A22D3THLEE/oneshot-horizon-builds)).

The phone downloads Minecraft's files from Mojang by itself, but part of what Horizon needs is
made by Java exporters running Mojang's game code (world generation, tags, block facts), and a
phone has no Java. The workflow here makes that part on GitHub's runner and publishes it as
`horizon-derived.zip`, one release per port commit (`derived-<first 12 hex of the commit>`). The
APK built from that commit downloads it on its first run.

How a pack is made (`.github/workflows/derived.yml`):
1. `tools/fetch_game.py` downloads the version pinned by the port's `research-lock.json` from
   Mojang's servers, every file checked by SHA-1.
2. The port's own `horizon-prepare` prepares Horizon's resources from it.
3. The port's `packaging/android/make_derived_pack.sh` keeps only what the phone cannot take
   from Mojang itself.

The workflow runs daily (it builds a pack only for a port commit that has none yet) and by hand.

Minecraft is a trademark of Mojang. This project is not affiliated with Mojang or Microsoft. The
packs are derived from Mojang's game files; they are removed on request.
