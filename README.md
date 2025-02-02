## 3D Filament Profiles Data

This repository contains a script to fetch/parse data from the [3D Filament Profiles](https://3dfilamentprofiles.com) website.

Public Resources:
* Filaments: https://3dfilamentprofiles.com/filaments [ [sample](./sample-filaments.json) / [raw](./sample-filaments-raw.rsc) ]
* Brands: https://3dfilamentprofiles.com/brands [ [sample](./sample-brands.json) / [raw](./sample-brands-raw.rsc) ]
* Materials: https://3dfilamentprofiles.com/materials
* Dryers: https://3dfilamentprofiles.com/dryers

Authenticated Resources:
* My Filaments: https://3dfilamentprofiles.com/my/filaments (requires authentication)

### Authentication

Some resources (like `myfilaments`) require authentication:

* Manual Authentication:
    1. Visit https://3dfilamentprofiles.com/my/filaments
    2. Open the browser's DevTools (F12) > Application > Cookies
    3. Copy the `*auth-token*` value(s) to `.env` (see [.env.example](./.env.example))

### Usage

Parse sample files:

`./parser.py --file ./sample-filaments-raw.rsc --resource filaments > sample-filaments.json`

Fetch and parse:

`./parser.py --fetch filaments > filaments.json`

Command line arguments:
```
usage: parser.py [-h] [--fetch RESOURCE] [--file FILE] [--resource RESOURCE]

options:
  -h, --help           show this help message and exit

Source:
  --fetch RESOURCE     Fetch one of: filaments, brands, materials, dryers, myfilaments
  --file FILE          path to the file to parse

Parse:
  --resource RESOURCE  Parse one of: filaments, brands, materials, dryers, myfilaments, raw; defaults to --fetch```

Examples:
```bash
# Fetch public filaments
./parser.py --fetch filaments > filaments.json

# Fetch authenticated user's filaments (requires AUTH_COOKIES in .env, see.env.example)
./parser.py --fetch myfilaments > my-filaments.json
```

### References

* https://3dfilamentprofiles.com | https://github.com/MarksMakerSpace/filament-profiles
* [RSC Devtools](https://chromewebstore.google.com/detail/rsc-devtools/jcejahepddjnppkhomnidalpnnnemomn) Chrome Extension based on https://github.com/alvarlagerlof/rsc-parser
