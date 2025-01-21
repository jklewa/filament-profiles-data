# Output Formats

## Bambu Lab Filaments

Joins data from `filaments.json` and `myfilaments.json` into a single json file in the format of Bambu Lab

Note: `filaments.json` is required, as it contains configuration options. `myfilaments.json` is an optional filter.

### Usage
```
usage: bambu_lab.py [-h] [--test] [--raw] [file] [myfile]

positional arguments:
  file        path to a filaments.json
  myfile      path to a myfilaments.json

optional arguments:
  -h, --help  show this help message and exit
  --test      Test models with data/filaments.json
  --raw       Output raw json instead of bambu_lab format
```

### Examples
```shell
# print sample data
python3 format/bambu_lab.py

# print sample data in model validated format
python3 format/bambu_lab.py --raw

# Joins data and prints my filaments in bambu format
python3 format/bambu_lab.py data/filaments.json data/myfilaments.json

# Print ALL filaments in bambu format
python3 format/bambu_lab.py data/filaments.json
```

### Sample Data

Output Structure: `{ [filename]: { [filament data] } }`

Filament Data:
- `name`: str Filament name
- `filament_settings_id`: list[str] Filament settings ID
- `inherits`: str Inherited filament settings ID
- `from`: str "system" or "User"
- `filament_vendor`: list[str] Filament vendor
- `version`: str Version of Bambu Studio
- ... various optional config values

```json
{
  "filaments/pla/123-3d-pla-basic-BBL-filament.json": {
    "name": "123-3D PLA Basic",
    "filament_type": [
      "PLA"
    ],
    "compatible_printers": [
      "Bambu Lab X1 Carbon 0.4 nozzle",
      "Bambu Lab X1 Carbon 0.6 nozzle",
      "Bambu Lab X1 Carbon 0.8 nozzle",
      "Bambu Lab P1S 0.4 nozzle",
      "Bambu Lab P1S 0.6 nozzle",
      "Bambu Lab P1S 0.8 nozzle",
      "Bambu Lab X1E 0.4 nozzle",
      "Bambu Lab X1E 0.6 nozzle",
      "Bambu Lab X1E 0.8 nozzle"
    ],
    "filament_settings_id": [
      "123-3D PLA Basic"
    ],
    "inherits": "Generic PLA",
    "from": "User",
    "is_custom_defined": "0",
    "filament_vendor": [
      "123-3D"
    ],
    "version": "1.10.1.50",
    "default_filament_colour": [
      "#000000"
    ],
    "nozzle_temperature_range_high": [
      "235"
    ],
    "nozzle_temperature_range_low": [
      "195"
    ],
    "hot_plate_temp": [
      "65"
    ],
    "hot_plate_temp_initial_layer": [
      "65"
    ],
    "textured_plate_temp": [
      "65"
    ],
    "textured_plate_temp_initial_layer": [
      "65"
    ],
    "temperature_vitrification": [
      "190"
    ],
    "fan_max_speed": [
      "100"
    ],
    "fan_min_speed": [
      "90"
    ],
    "filament_flow_ratio": [
      "0.98"
    ],
    "filament_max_volumetric_speed": [
      "12"
    ],
    "filament_cost": [
      "29"
    ],
    "filament_retraction_minimum_travel": [
      "2.5"
    ]
  }
}
```

### Import into Bambu Studio
Split the output into multiple files and import them into Bambu Studio.

```python
import json
with open('output.json', 'r') as f:
    # Data format: { [filename]: { [filament data] } }
    for k, v in json.load(f).items():
        with open(k, 'w') as f2:
            json.dump(v, f2, indent=4)
```

Configs can be imported using **Bambu Studio > File > Import > Import Configs...**

The import will save the files under `~/Library/Application\ Support/BambuStudio/user/*/filament/` on macOS.