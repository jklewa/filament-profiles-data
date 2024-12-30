#!/usr/bin/env python3
import argparse
import json
import re
import sys
from typing import Any, Dict, Optional, Union

import pydantic
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_serializer


class Image(BaseModel):
    height: int
    url: str
    width: int


class PriceData(BaseModel):
    price: Union[float, int, None] = None
    bad: Optional[str] = None

    asin: Optional[str] = None
    href: Optional[str] = None
    image: Optional[Image] = None
    image_med: Optional[Image] = None
    listings: Optional[list] = None
    manufacturer: Optional[str] = None
    merchant: Optional[str] = None
    price_date: Optional[str] = None
    primeOnly: Optional[bool] = None
    title: Optional[str] = None

    @model_serializer(when_used="json")
    def serialize_json(self) -> Dict[str, Any]:
        model = dict(sorted(self.model_dump().items()))
        return {
            key: value
            for key, value in model.items()
            if value is not None and value != {}
        }


class Filament(BaseModel):
    ASIN: Optional[str]
    adapterUrl: Optional[str]
    bed_temp_max: Optional[int] = None
    bed_temp_min: Optional[int] = None
    brand_id: str
    brand_name: str
    color: str
    created_at: str = Field(
        validation_alias=AliasChoices("created_at", "filament_created_at")
    )
    created_by: Optional[str] = None
    deleted: Optional[str] = None
    fan_speed_max: Optional[int] = None
    fan_speed_min: Optional[int] = None
    flow_ratio: Union[float, int, None] = None
    id: int = Field(validation_alias=AliasChoices("id", "filament_id"))
    image: Optional[str] = None
    kValue: Union[float, int, None] = None
    material: str
    material_id: str
    material_type: str
    material_type_id: str
    max_volumetric_speed: Union[float, int, None] = None
    priceData: Union[PriceData, str, None] = Field(
        None, validation_alias=AliasChoices("priceData", "price_data")
    )
    purchaseLink: Optional[str] = None
    rgb: Optional[str]
    softening_temp: Union[float, int, None] = None
    spool_count: Optional[int] = None
    spoolWeight: Union[float, int, None] = Field(
        None, validation_alias=AliasChoices("spoolWeight", "empty_spool_weight")
    )
    td_value: Union[float, int, None] = None
    temp_max: Optional[int] = None
    temp_min: Optional[int] = None
    total_td_votes: Optional[int] = None
    updated_at: str = Field(
        validation_alias=AliasChoices("updated_at", "filament_updated_at")
    )
    updated_by: Optional[str] = None

    model_config = ConfigDict(strict=True, extra="ignore")

    def to_bambu_lab_filament_format(self):
        bambu_lab_filament_json = {
            "type": "filament",
            "name": " ".join(
                filter(None, [self.brand_name, self.material, self.material_type])
            ),
            "inherits": f"fdm_filament_{self.material_id}",
            "from": "system",
            "filament_vendor": [self.brand_name],
        }
        if self.temp_max is not None or self.temp_min is not None:
            if self.temp_max is not None:
                bambu_lab_filament_json.update(
                    {
                        "nozzle_temperature_range_high": [self.temp_max],
                    }
                )
            if self.temp_min is not None:
                bambu_lab_filament_json.update(
                    {
                        "nozzle_temperature_range_low": [self.temp_min],
                    }
                )
        if self.bed_temp_min is not None or self.bed_temp_max is not None:
            best_temp = (
                self.bed_temp_max or self.bed_temp_min
            )  # todo: better logic to determine best temp from range
            bambu_lab_filament_json.update(
                {
                    "hot_plate_temp": [f"{best_temp}"],
                    "hot_plate_temp_initial_layer": [f"{best_temp}"],
                    # "cool_plate_temp": [f"{best_temp}"],
                    # "cool_plate_temp_initial_layer": [f"{best_temp}"],
                    # "supertack_plate_temp": [f"{best_temp}"],
                    # "supertack_plate_temp_initial_layer": [f"{best_temp}"],
                }
            )
        if self.fan_speed_max is not None or self.fan_speed_min is not None:
            if self.fan_speed_max is not None:
                bambu_lab_filament_json.update(
                    {
                        "fan_max_speed": [f"{self.fan_speed_max}"],
                    }
                )
            if self.fan_speed_min is not None:
                bambu_lab_filament_json.update(
                    {
                        "fan_min_speed": [f"{self.fan_speed_min}"],
                    }
                )
        if self.flow_ratio is not None:
            bambu_lab_filament_json.update(
                {
                    "filament_flow_ratio": [f"{self.flow_ratio:.2f}"],
                }
            )
        if self.max_volumetric_speed is not None:
            bambu_lab_filament_json.update(
                {
                    "filament_max_volumetric_speed": [self.max_volumetric_speed],
                }
            )
        if getattr(self.priceData, "price", None):
            bambu_lab_filament_json.update(
                {
                    "filament_cost": [f"{self.priceData.price:.2f}"],
                }
            )
        # Unmapped fields:
        # color: str
        # rgb: Optional[str]
        # kValue: Union[float, int, None]
        # softening_temp: Union[float, int, None]
        # spoolWeight: Union[float, int, None]
        # td_value: Union[float, int, None]
        # total_td_votes: Optional[int]
        return bambu_lab_filament_json


class MyFilament(Filament):
    # Renamed fields
    empty_spool_weight: Union[float, int, None] = Field(
        None, alias="spoolWeight", validation_alias=AliasChoices("spoolWeight", "empty_spool_weight")
    )
    spoolWeight: Union[float, int, None] = Field(exclude=True)
    filament_created_at: str = Field(
        alias="created_at", validation_alias=AliasChoices("created_at", "filament_created_at")
    )
    created_at: str = Field(exclude=True)
    filament_id: int = Field(
        alias="id", validation_alias=AliasChoices("id", "filament_id")
    )
    id: int = Field(exclude=True)
    filament_updated_at: str = Field(
        alias="updated_at", validation_alias=AliasChoices("updated_at", "filament_updated_at")
    )
    updated_at: str = Field(exclude=True)
    price_data: Union[PriceData, str, None] = Field(
        None, alias="priceData", validation_alias=AliasChoices("priceData", "price_data")
    )
    priceData: Union[PriceData, str, None] = Field(exclude=True)

    # Additional fields
    last_updated: str
    total_remaining_grams: Union[float, int, None]
    user_id: str


def slugify(s: str) -> str:
    return re.sub(r"\W+", "-", s).strip("-").lower()


def remove_none_values(d):
    if isinstance(d, dict):
        return {k: remove_none_values(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [remove_none_values(i) for i in d]
    return d


def test_models():
    # Test models with larger dataset
    with open("data/filaments.json", "r") as f:
        filament_data = json.load(f)
        for filament in filament_data["filaments"]:
            try:
                base = Filament.model_validate(filament)
                raw_json = json.dumps(
                    remove_none_values(filament),
                    separators=(",", ":"),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                model_json = base.model_dump_json(exclude_none=True)
                if raw_json != model_json:
                    print("Mismatch")
                    print(raw_json)
                    print(model_json)
                # break
            except pydantic.ValidationError as e:
                print(e)
                print(filament)
                break


# Test model example
_base_example = """
    {
      "id": 1802,
      "created_at": "2024-12-19T15:57:04.962+00:00",
      "color": "Zwart",
      "rgb": "#000000",
      "image": "/images/filaments/metallic_silver.jpg",
      "kValue": 0.05,
      "spoolWeight": 216,
      "adapterUrl": null,
      "purchaseLink": "https://www.123-3d.nl/123-3D-Filament-zwart-1-75-mm-PLA-1-1-kg-Jupiter-serie-i9729-t7316.html",
      "ASIN": null,
      "priceData": {
        "title": "3D-Fuel Standard PLA+ Filament for 3D Printing, Made in The USA, 3D Printer Filament, Dimensional Accuracy +/- 0.02 mm, 1.75 mm, 1 kg Spool, Midnight Black",
        "price": 29,
        "primeOnly": false,
        "href": "https://www.amazon.com/dp/B01DXWQM6M?tag=3dfil-20&linkCode=ogi&th=1&psc=1&language=en_US",
        "image": {
          "url": "https://m.media-amazon.com/images/I/51Vb0-PDIcL._SL75_.jpg",
          "width": 75,
          "height": 56
        },
        "image_med": {
          "url": "https://m.media-amazon.com/images/I/51Vb0-PDIcL._SL160_.jpg",
          "width": 160,
          "height": 120
        },
        "asin": "B01DXWQM6M",
        "price_date": "2024-12-21T01:45:34.945Z",
        "listings": [
          {
            "price": {
              "amount": 29,
              "currency": "USD",
              "savings": {
                "amount": 0,
                "currency": "USD",
                "percentage": 0
              }
            }
          }
        ]
      },
      "flow_ratio": 0.98,
      "temp_min": 195,
      "temp_max": 235,
      "fan_speed_min": null,
      "fan_speed_max": null,
      "softening_temp": null,
      "max_volumetric_speed": 12,
      "bed_temp_min": 55,
      "bed_temp_max": 75,
      "created_by": "f8bc55a7-a4e9-4823-9cc9-d93fba5febc7",
      "updated_at": "2024-12-19T16:08:28.114+00:00",
      "updated_by": "f8bc55a7-a4e9-4823-9cc9-d93fba5febc7",
      "deleted": null,
      "brand_id": "123-3d",
      "material_id": "pla",
      "material_type_id": "basic",
      "brand_name": "123-3D",
      "material": "PLA",
      "material_type": "Basic",
      "td_value": 0,
      "total_td_votes": 0
    }
    """


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "file", nargs="?", type=argparse.FileType("r"), help="path to a filaments.json"
    )
    parser.add_argument(
        "myfile", nargs="?", type=argparse.FileType("r"), help="path to a myfilaments.json"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test models with data/filaments.json"
    )
    parser.add_argument(
        "--raw", action="store_true", help="Output raw json instead of bambu_lab format"
    )
    args = parser.parse_args()

    if args.test:
        test_models()
        exit(0)

    if args.file is None and args.myfile is None:
        print("No file provided. Using example data", file=sys.stderr)
        filaments = [json.loads(_base_example)]
    else:
        filaments = json.load(args.file)["filaments"]
    if args.myfile is not None:
        my_filaments = {filament["filament_id"]: filament for filament in json.load(args.myfile)["filaments"]}
    else:
        my_filaments = None
    results = {}
    for filament in filaments:
        validation_class = Filament
        if my_filaments:
            if filament["id"] not in my_filaments:
                continue
            validation_class = MyFilament
            extra = my_filaments[filament["id"]]
            filament.update(extra)
        try:
            f: MyFilament = validation_class.model_validate(filament)
            filename = slugify(f"{f.brand_id}-{f.material_id}-{f.material_type_id}") + ".json"
            results[filename] = f.model_dump(mode="json") if args.raw else f.to_bambu_lab_filament_format()
        except pydantic.ValidationError as e:
            print(e, file=sys.stderr)
            print(filament, file=sys.stderr)
            exit(1)
    print(json.dumps(results, indent=2))
