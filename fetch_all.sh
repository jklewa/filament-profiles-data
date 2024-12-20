set -x
mkdir -p data
python3 ./parser.py --fetch filaments > data/filaments.json
python3 ./parser.py --fetch brands > data/brands.json
python3 ./parser.py --fetch materials > data/materials.json
python3 ./parser.py --fetch dryers > data/dryers.json
