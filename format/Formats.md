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

Structure: `{ [filename]: { [filament data] } }`

```json
{
  "123-3d-pla-basic.json": {
    "type": "filament",
    "name": "123-3D PLA Basic",
    "inherits": "fdm_filament_pla",
    "from": "system",
    "filament_vendor": [
      "123-3D"
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
    "filament_flow_ratio": [
      "0.98"
    ],
    "filament_max_volumetric_speed": [
      "12"
    ],
    "filament_cost": [
      "29.00"
    ]
  }
}
```