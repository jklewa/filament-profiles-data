## 3D Filament Profiles Data

This repository contains a script to fetch/parse data from the [3D Filament Profiles](https://3dfilamentprofiles.com) website.

* Filaments: https://3dfilamentprofiles.com/filaments [ [sample](./sample-filaments.json) / [raw](./sample-filaments-raw.json) ]
* Brands: https://3dfilamentprofiles.com/brands [ [sample](./sample-brands.json) / [raw](./sample-brands-raw.json) ]
* Materials: https://3dfilamentprofiles.com/materials
* Dryers: https://3dfilamentprofiles.com/dryers

### Usage

Parse sample files:

`./parser.py --file ./sample-filaments-raw.json --resource filaments > sample-filaments.json`

Fetch and parse:

`./parser.py --fetch filaments > filaments.json`

Command line arguments:
```
usage: parser.py [-h] [--fetch RESOURCE] [--file FILE] [--resource RESOURCE]

optional arguments:
  -h, --help           show this help message and exit

Source:
  --fetch RESOURCE     Fetch one of: filaments, brands, materials, dryers
  --file FILE          path to the file to parse

Parse:
  --resource RESOURCE  Parse one of: filaments, brands, materials, dryers; defaults to --fetch
```

### References

* 3D Filament Profiles Project: https://github.com/MarksMakerSpace/filament-profiles