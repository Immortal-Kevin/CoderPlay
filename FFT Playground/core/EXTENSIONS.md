# Stable engine boundary

`Parameters` → `generate()` / `analyze()` → `Analysis` is the public interface.
Engine modules import only the Python standard library and never import UI,
networking, game code, or proprietary data. Keep imported arrays unchanged.

Future game modules should live in a separate package and call this interface.
They can have their own launcher, assets, distribution and license notices.
There is deliberately no dynamic plugin loader or game implementation in v1.0.
New original modules may use proprietary licenses; Apache-2.0 rights already
granted for this release remain in effect. Preserve LICENSE/NOTICE and identify
changes when redistributing or modifying the Apache core.
