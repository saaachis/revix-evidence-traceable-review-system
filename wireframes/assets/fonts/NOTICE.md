# Wordmark font

`revix-wordmark.woff2` is **Playfair Display**, weight 900 **italic**, by Claus Eggers
Sorensen, obtained from Google Fonts. This is the real italic cut, not a slanted roman, so the
letterforms are genuinely calligraphic rather than mechanically skewed.

| | |
|---|---|
| Licence | SIL Open Font License 1.1, see `LICENSE.txt` |
| Modification | Subset to the five lowercase letters of "revix". No outlines were altered. |
| Size | 1,556 bytes |
| Why embedded | The subset is inlined as a `data:` URI in `assets/revix.css`, so the wordmark renders identically offline, from `file://`, and on GitHub Pages. No network request, nothing to fail during a demo. |

## The lockup

Lowercase throughout. The mark is `revix` in lowercase italic, which suits this word well because
none of its five letters has a descender, so it sits cleanly on the baseline while the italic gives
it movement. The descriptor `driven by reviews` is lowercase too, smaller and letter-spaced, set
upright in the interface sans so it does not compete with the mark.
