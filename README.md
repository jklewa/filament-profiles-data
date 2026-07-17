## 3D Filament Profiles Data

This repository contains scripts to fetch filament data from [3D Filament Profiles](https://3dfilamentprofiles.com) and convert it to Bambu Lab / OrcaSlicer preset files.

Public Resources:
* Filaments: https://3dfilamentprofiles.com/filaments [ [sample](./sample-filaments.json) / [raw](./sample-filaments-raw.rsc) ]
* Brands: https://3dfilamentprofiles.com/brands [ [sample](./sample-brands.json) / [raw](./sample-brands-raw.rsc) ]
* Materials: https://3dfilamentprofiles.com/materials
* Dryers: https://3dfilamentprofiles.com/dryers

Authenticated Resources:
* My Filaments: https://3dfilamentprofiles.com/my/filaments (requires authentication)

### Authentication

Some resources (like `myfilaments`) require authentication:

1. Visit https://3dfilamentprofiles.com/my/filaments
2. Open the browser's DevTools (F12) > Application > Cookies
3. Copy the `*auth-token*` value(s) to `.env` (see [.env.example](./.env.example))

---

### Full Pipeline: Fetch All Filaments → Bambu/OrcaSlicer Presets

```bash
# Fetch all ~30k filaments with full data (rgb, temps, fan, flow, price, etc.)
# Slow — makes ~2 HTTP requests per brand/material/type combo (~2000+ total)
./parser.py --fetch filaments > filaments.json

# Convert to slicer presets — one .json per color, written to a directory
python3 format/bambu_lab.py filaments.json --dir /path/to/presets/filament/

# Or output a single JSON map of filename -> preset to stdout
python3 format/bambu_lab.py filaments.json
```

The output files inherit from the appropriate `Generic <MATERIAL>` base profile and include:
- `nozzle_temperature_range_low/high` (`temp_min`/`temp_max`)
- `hot_plate_temp`, `textured_plate_temp` (`bed_temp_min/max`)
- `fan_min_speed`, `fan_max_speed`
- `filament_flow_ratio`
- `default_filament_colour` (RGB hex, comma-separated for dual-color)
- `filament_cost` (from price data)

---

### Other Fetch Options

```bash
./parser.py --fetch brands > brands.json
./parser.py --fetch materials > materials.json
./parser.py --fetch dryers > dryers.json

# Authenticated user's filaments (requires AUTH_COOKIES in .env)
./parser.py --fetch myfilaments > my-filaments.json

# Parse a saved raw RSC file
./parser.py --file ./sample-filaments-raw.rsc --resource filaments > sample-filaments.json
```

---

### Command Reference

**parser.py:**
```
usage: parser.py [-h] [--debug] [--fetch RESOURCE] [--file FILE] [--resource RESOURCE]

  --debug          Enable debug output
  --fetch          filaments   Full enriched fetch (rgb, temps, fan, flow, price) — use this
                   brands / materials / dryers / myfilaments
  --file FILE      Path to a raw RSC file to parse
  --resource       Resource type for --file: filaments, brands, materials, dryers, myfilaments, raw
```

**format/bambu_lab.py:**
```
usage: bambu_lab.py [file] [myfile] [--raw] [--dir DIR]

  file       filaments.json from parser.py --fetch filaments
  myfile     myfilaments.json (filters output to owned spools only)
  --raw      Output validated model JSON instead of slicer preset format
  --dir DIR  Write one .json per filament into DIR/filaments/<material>/
```

---

### References

* https://3dfilamentprofiles.com | https://github.com/MarksMakerSpace/filament-profiles
* [RSC Devtools](https://chromewebstore.google.com/detail/rsc-devtools/jcejahepddjnppkhomnidalpnnnemomn) Chrome Extension based on https://github.com/alvarlagerlof/rsc-parser
