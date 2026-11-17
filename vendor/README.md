# Vendored code

Kept in the repository so the example and the tests need no network and no install step.

## `board-generator/` · Board Generator 1.1

From [github.com/chalouhi/board-generator](https://github.com/chalouhi/board-generator) at tag `v1.1`, unchanged, under the MIT licence (`board-generator/LICENSE`). The example's page is drawn by `src/board.js`; the tests run its reader on every file the extractor writes; `src/picture.js` makes the front page's picture.

| File | From `v1.1` | SHA-256 |
|---|---|---|
| `board-generator/src/board.js` | `src/board.js` | `c25d623deed1cd979169315c9dff69fae334a98f71aa0dd43ce082888c58c725` |
| `board-generator/src/picture.js` | `src/picture.js` | `defb3116cdeb80f0bdd59602aae1150912065afeaf9a87ac37682e4de3cd6235` |
| `board-generator/src/fontsubset.js` | `src/fontsubset.js` | `191d6c9920b326d9f8127d1095e0cb724dd003e91a4d6017cad13ab60de5ccb4` |
| `board-generator/vendor/fontkit.umd.min.js` | `vendor/fontkit.umd.min.js` | `d8df561b9fba98e24f2e5130e40948809281bbbc55a20c412359f1a0a5eb35a6` |
| `board-generator/fonts/Carlito-Regular.ttf` | `fonts/Carlito-Regular.ttf` | `f6418f708baede9789daef5d458c0f53d2a888af9820e8062934e504fedc6595` |
| `board-generator/fonts/Carlito-Bold.ttf` | `fonts/Carlito-Bold.ttf` | `bb5d20f79b82599ec72983597437373a80f2d2085fa91fc144fd74e876a594db` |
| `board-generator/fonts/OFL.txt` | `fonts/OFL.txt` | `11b9998b80c86f7d40d6ec891fdf7daf4c7c8fbabd09c4f2bd6c99be618b3f32` |
| `board-generator/LICENSE` | `LICENSE` | `3575f845cb81b091469800a89f03a56320943848ff2a8fe97d7830fd62806176` |

- `fontkit.umd.min.js` is @pdf-lib/fontkit 1.1.1 (https://github.com/Hopding/fontkit), MIT (Andrew Dillon, Devon Govett).
- The fonts are Carlito, Regular and Bold, metric-compatible with Calibri, under the SIL Open Font Licence 1.1 (`board-generator/fonts/OFL.txt`). "Carlito" is a Reserved Font Name; the cut-down copy inside the picture is named "Board Sans", as the Board Generator does.

`tests/vendor.test.js` checks every file against its SHA-256.
