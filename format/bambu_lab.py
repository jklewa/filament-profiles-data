import pydantic
from pydantic import (
    BaseModel,
    ConfigDict,
    Tag,
    Discriminator,
    model_serializer,
)
from typing import Dict, Optional, Union, Any
from typing_extensions import Annotated


class Image(BaseModel):
    height: int
    url: str
    width: int


class PriceData(BaseModel):
    asin: Optional[str] = None
    href: str
    image: Image
    image_med: Optional[Image] = None
    listings: list
    manufacturer: Optional[str] = None
    merchant: Optional[str] = None
    price: Union[float, int]
    price_date: str
    primeOnly: bool
    title: str

    @model_serializer(when_used="json")
    def serialize_json(self) -> Dict[str, Any]:
        model = dict(sorted(self.model_dump(exclude_none=True).items()))
        return {
            key: value
            for key, value in model.items()
            if value is not None and value != {}
        }


class BadPriceData(BaseModel):
    bad: str


class MixedPriceData(PriceData):
    bad: Optional[str] = None
    price: Union[float, int, None] = None


def get_price_data_discriminator_value(obj):
    if isinstance(obj, dict):
        if "title" in obj:
            if "bad" in obj:
                return "mixed"
            return "price"
        return "bad"
    elif isinstance(obj, str):
        return "str"
    elif obj is None:
        return "none"


class Base(BaseModel):
    ASIN: Optional[str]
    adapterUrl: Optional[str]
    bed_temp_max: Optional[int]
    bed_temp_min: Optional[int]
    brand_id: str
    brand_name: str
    color: str
    created_at: str
    created_by: str
    deleted: Optional[str]
    fan_speed_max: Optional[int]
    fan_speed_min: Optional[int]
    flow_ratio: Union[float, int, None]
    id: int
    image: Optional[str]
    kValue: Union[float, int, None]
    material: str
    material_id: str
    material_type: str
    material_type_id: str
    max_volumetric_speed: Union[float, int, None]
    priceData: Annotated[
        Union[
            Annotated[PriceData, Tag("price")],
            Annotated[BadPriceData, Tag("bad")],
            Annotated[MixedPriceData, Tag("mixed")],
            Annotated[str, Tag("str")],
            Annotated[None, Tag("none")],
        ],
        Discriminator(get_price_data_discriminator_value),
    ]
    purchaseLink: Optional[str]
    rgb: Optional[str]
    softening_temp: Union[float, int, None]
    spoolWeight: Union[float, int, None]
    td_value: Union[float, int, None]
    temp_max: Optional[int]
    temp_min: Optional[int]
    total_td_votes: Optional[int]
    updated_at: str
    updated_by: str

    model_config = ConfigDict(strict=True)

    def to_bambu_lab_filament_json(self):
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


if __name__ == "__main__":
    # Test models with larger dataset
    with open("data/filaments.json", "r") as f:
        import json

        filament_data = json.load(f)
        for filament in filament_data["filaments"]:
            try:
                base = Base.model_validate(filament)
                raw_json = json.dumps(
                    filament, separators=(",", ":"), ensure_ascii=False, sort_keys=True
                )
                model_json = base.model_dump_json()
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
    base_example = """
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

    base = Base.model_validate_json(base_example)
    print(json.dumps(base.to_bambu_lab_filament_json(), indent=2))
