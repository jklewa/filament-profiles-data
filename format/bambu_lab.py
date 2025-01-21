#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import sys
from typing import Any, Dict, Optional, Union
from unittest.mock import ANY

import pydantic
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_serializer

bambu_studio_version = "1.10.1.50"
# https://github.com/bambulab/BambuStudio/tree/98bfabdd/resources/profiles/BBL/filament
profiles_available = {
    "Generic ABS @0.2 nozzle", "Generic ABS @BBL A1 0.2 nozzle", "Generic ABS @BBL A1",
    "Generic ABS @BBL X1E 0.2 nozzle", "Generic ABS @BBL X1E", "Generic ABS @base", "Generic ABS",
    "Generic ASA @0.2 nozzle", "Generic ASA @BBL A1 0.2 nozzle", "Generic ASA @BBL A1",
    "Generic ASA @BBL X1E 0.2 nozzle", "Generic ASA @BBL X1E", "Generic ASA @base", "Generic ASA",
    "Generic BVOH @BBL A1", "Generic BVOH @BBL A1M", "Generic BVOH @BBL X1C", "Generic BVOH @base",
    "Generic EVA @BBL A1", "Generic EVA @BBL A1M", "Generic EVA @BBL X1C", "Generic EVA @base",
    "Generic HIPS @BBL A1 0.2 nozzle", "Generic HIPS @BBL A1", "Generic HIPS @BBL A1M 0.2 nozzle",
    "Generic HIPS @BBL A1M", "Generic HIPS @BBL X1C 0.2 nozzle", "Generic HIPS @BBL X1C", "Generic HIPS @base",
    "Generic PA @BBL A1", "Generic PA-CF @BBL A1", "Generic PA-CF @BBL X1E", "Generic PA-CF", "Generic PA",
    "Generic PC @0.2 nozzle", "Generic PC @BBL A1 0.2 nozzle", "Generic PC @BBL A1", "Generic PC @BBL P1S 0.2 nozzle",
    "Generic PC @BBL P1S", "Generic PC @BBL X1E 0.2 nozzle", "Generic PC @BBL X1E", "Generic PC @base", "Generic PC",
    "Generic PCTG @BBL A1", "Generic PCTG @BBL A1M", "Generic PCTG @BBL X1C", "Generic PCTG @base",
    "Generic PE @BBL A1", "Generic PE @BBL A1M", "Generic PE @BBL X1C", "Generic PE @base", "Generic PE-CF @BBL A1",
    "Generic PE-CF @BBL A1M", "Generic PE-CF @BBL X1C", "Generic PE-CF @base", "Generic PETG @0.2 nozzle",
    "Generic PETG @BBL A1 0.2 nozzle", "Generic PETG @BBL A1", "Generic PETG @BBL A1M 0.2 nozzle",
    "Generic PETG @BBL A1M", "Generic PETG @base", "Generic PETG HF @BBL A1 0.2 nozzle", "Generic PETG HF @BBL A1",
    "Generic PETG HF @BBL A1M 0.2 nozzle", "Generic PETG HF @BBL A1M", "Generic PETG HF @BBL P1P 0.2 nozzle",
    "Generic PETG HF @BBL P1P", "Generic PETG HF @BBL X1C 0.2 nozzle", "Generic PETG HF @BBL X1C",
    "Generic PETG HF @base", "Generic PETG-CF @BBL A1", "Generic PETG-CF @BBL X1C", "Generic PETG-CF @base",
    "Generic PETG", "Generic PHA @BBL A1", "Generic PHA @BBL A1M", "Generic PHA @BBL X1C", "Generic PHA @base",
    "Generic PLA @0.2 nozzle", "Generic PLA @BBL A1 0.2 nozzle", "Generic PLA @BBL A1",
    "Generic PLA @BBL A1M 0.2 nozzle", "Generic PLA @BBL A1M", "Generic PLA @base",
    "Generic PLA High Speed @BBL A1 0.2 nozzle", "Generic PLA High Speed @BBL A1",
    "Generic PLA High Speed @BBL A1M 0.2 nozzle", "Generic PLA High Speed @BBL A1M",
    "Generic PLA High Speed @BBL P1P 0.2 nozzle", "Generic PLA High Speed @BBL P1P",
    "Generic PLA High Speed @BBL X1C 0.2 nozzle", "Generic PLA High Speed @BBL X1C", "Generic PLA High Speed @base",
    "Generic PLA Silk @BBL A1", "Generic PLA Silk @BBL A1M", "Generic PLA Silk @base", "Generic PLA Silk",
    "Generic PLA-CF @BBL A1", "Generic PLA-CF @BBL A1M", "Generic PLA-CF @base", "Generic PLA-CF", "Generic PLA",
    "Generic PP @BBL A1", "Generic PP @BBL A1M", "Generic PP @BBL X1C", "Generic PP @base", "Generic PP-CF @BBL A1",
    "Generic PP-CF @BBL X1C", "Generic PP-CF @base", "Generic PP-GF @BBL A1", "Generic PP-GF @BBL X1C",
    "Generic PP-GF @base", "Generic PPA-CF @BBL X1C", "Generic PPA-CF @BBL X1E", "Generic PPA-CF @base",
    "Generic PPA-GF @BBL X1C", "Generic PPA-GF @BBL X1E", "Generic PPA-GF @base", "Generic PPS @BBL X1E",
    "Generic PPS @base", "Generic PPS-CF @BBL X1E", "Generic PPS-CF @base", "Generic PVA @0.2 nozzle",
    "Generic PVA @BBL A1 0.2 nozzle", "Generic PVA @BBL A1", "Generic PVA @BBL A1M 0.2 nozzle", "Generic PVA @BBL A1M",
    "Generic PVA @base", "Generic PVA", "Generic TPU @BBL A1", "Generic TPU @BBL A1M", "Generic TPU for AMS @BBL A1",
    "Generic TPU for AMS @BBL A1M", "Generic TPU for AMS @BBL P1P", "Generic TPU for AMS @BBL X1C",
    "Generic TPU for AMS @base", "Generic TPU", "Generic ABS @BBL P1P 0.2 nozzle", "Generic ABS @BBL P1P",
    "Generic ASA @BBL P1P 0.2 nozzle", "Generic ASA @BBL P1P", "Generic PA @BBL P1P", "Generic PA-CF @BBL P1P",
    "Generic PC @BBL P1P 0.2 nozzle", "Generic PC @BBL P1P", "Generic PETG @BBL P1P 0.2 nozzle",
    "Generic PETG @BBL P1P", "Generic PETG-CF @BBL A1M", "Generic PETG-CF @BBL P1P", "Generic PLA @BBL P1P 0.2 nozzle",
    "Generic PLA @BBL P1P", "Generic PLA Silk @BBL P1P", "Generic PLA-CF @BBL P1P", "Generic PVA @BBL P1P 0.2 nozzle",
    "Generic PVA @BBL P1P", "Generic TPU @BBL P1P", "Bambu PET-CF @BBL A1", "Bambu PET-CF @BBL X1C",
    "Bambu PET-CF @BBL X1E", "Bambu PET-CF @BBL P1P", "Bambu PET-CF @base", "fdm_filament_abs", "fdm_filament_asa",
    "fdm_filament_bvoh", "fdm_filament_common", "fdm_filament_eva", "fdm_filament_hips", "fdm_filament_pa",
    "fdm_filament_pc", "fdm_filament_pctg", "fdm_filament_pe", "fdm_filament_pet", "fdm_filament_pha",
    "fdm_filament_pla", "fdm_filament_pp", "fdm_filament_ppa", "fdm_filament_pps", "fdm_filament_pva",
    "fdm_filament_tpu",
}

# A mapping of material_key and material_type_key to base profile
# Order is important, generic -> specific, lowest in list wins
base_profiles = [
    ("abs", ANY, "Generic ABS"),
    ("abs-plus", ANY, "Generic ABS"),
    ("asa", ANY, "Generic ASA"),
    ("asa-plus", ANY, "Generic ASA"),
    ("hips", ANY, "Generic HIPS @BBL X1C"),
    ("pa", ANY, "Generic PA"),
    ("pa", "cf", "Generic PA-CF"),
    ("pa12", ANY, "Generic PA"),
    ("pa6", ANY, "Generic PA"),
    ("pa612", ANY, "Generic PA"),
    ("paht", ANY, "Generic PA"),
    ("pa", "ht", "Generic PA"),
    ("pc", ANY, "Generic PC"),
    ("pctg", ANY, "Generic PCTG @BBL X1C"),
    ("pe", ANY, "Generic PE"),
    ("pe", "cf", "Generic PE-CF @BBL X1C"),
    ("pet", ANY, "fdm_filament_pet"),
    ("pet", "cf", "Bambu PET-CF @BBL X1C"),
    ("petg", ANY, "Generic PETG"),
    ("petg", "cf", "Generic PETG-CF @BBL X1C"),
    ("petg-plus", ANY, "Generic PETG"),
    ("pla", ANY, "Generic PLA"),
    ("pla", "cf", "Generic PLA-CF"),
    ("pla-plus", ANY, "Generic PLA"),
    ("pla-plus-cf", ANY, "Generic PETG-CF @BBL X1C"),
    ("pp", ANY, "Generic PP"),
    ("pp", "cf", "Generic PP-CF @BBL X1C"),
    ("ppa", ANY, "Generic PPA"),
    ("ppa", "cf", "Generic PPA-CF @BBL X1C"),
    ("pps", ANY, "Generic PPS"),
    ("pps", "cf", "Generic PPS-CF @BBL X1E"),
    ("pva", ANY, "Generic PVA"),
    ("tpu", ANY, "Generic TPU"),
]

filament_types_available = {
    # https://github.com/bambulab/BambuStudio/blob/98bfabdd/src/slic3r/GUI/CreatePresetsDialog.cpp#L43
    "PLA", "PLA+", "PLA Tough", "PETG", "ABS", "ASA", "FLEX", "HIPS", "PA", "PACF", "NYLON", "PVA", "PC", "PCABS",
    "PCTG", "PCCF", "PP", "PEI", "PET", "PETG", "PETGCF", "PTBA", "PTBA90A", "PEEK", "TPU93A", "TPU75D", "TPU",
    "TPU-AMS", "TPU92A", "TPU98A", "Misc", "TPE", "GLAZE", "Nylon", "CPE", "METAL", "ABST", "Carbon Fiber",
    # https://github.com/bambulab/BambuStudio/blob/98bfabdd/src/libslic3r/PrintConfig.cpp#L1572
    "PLA", "ABS", "ASA", "ASA-CF", "PETG", "PCTG", "TPU", "TPU-AMS", "PC", "PA", "PA-CF", "PA-GF", "PA6-CF", "PLA-CF",
    "PET-CF", "PETG-CF", "PVA", "HIPS", "PLA-AERO", "PPS", "PPS-CF", "PPA-CF", "PPA-GF", "ABS-GF", "ASA-Aero", "PE",
    "PP", "EVA", "PHA", "BVOH", "PE-CF", "PP-CF", "PP-GF",
    # https://github.com/SoftFever/OrcaSlicer/blob/2ea2ab08/src/slic3r/GUI/CreatePresetsDialog.cpp#L62C57-L65C139
    "PLA", "rPLA", "PLA+", "PLA Tough", "PETG", "ABS", "ASA", "FLEX", "HIPS", "PA", "PACF", "NYLON", "PVA", "PVB", "PC",
    "PCABS", "PCTG", "PCCF", "PHA", "PP", "PEI", "PET", "PETGCF", "PTBA", "PTBA90A", "PEEK", "TPU93A", "TPU75D", "TPU",
    "TPU92A", "TPU98A", "Misc", "TPE", "GLAZE", "Nylon", "CPE", "METAL", "ABST", "Carbon Fiber", "SBS",
}

# A mapping of material_key and material_type_key to filament type
# Order is important, generic -> specific, lowest in list wins
filament_types = [
    ("abs", ANY, "ABS"),
    ("abs-plus", ANY, "ABS"),
    ("asa", ANY, "ASA"),
    ("asa", "aero", "ASA-Aero"),
    ("asa", "cf", "ASA-CF"),
    ("asa-plus", ANY, "ASA"),
    ("hips", ANY, "HIPS"),
    ("pa", ANY, "PA"),
    ("pa", "cf", "PA-CF"),
    ("pa12", ANY, "PA"),
    ("pa6", ANY, "PA"),
    ("pa6", "cf", "PA6-CF"),
    ("pa612", ANY, "PA"),
    ("paht", ANY, "PA"),
    ("pa", "ht", "PA"),
    ("pc", ANY, "PC"),
    ("pc", "cf", "PCCF"),
    ("pcabs", ANY, "PCABS"),
    ("pctg", ANY, "PCTG"),
    ("pe", ANY, "PE"),
    ("pe", "cf", "PE-CF"),
    ("pet", ANY, "PET"),
    ("pet", "cf", "PET-CF"),
    ("petg", ANY, "PETG"),
    ("petg", "cf", "PETG-CF"),
    ("petg-plus", ANY, "PETG"),
    ("pla", ANY, "PLA"),
    ("pla", "aero", "PLA-AERO"),
    ("pla", "cf", "PLA-CF"),
    ("pla-plus", ANY, "PLA+"),
    ("pla-plus-cf", ANY, "PLA+"),
    ("pp", ANY, "PP"),
    ("pp", "cf", "PP-CF"),
    ("ppa", ANY, "PPA"),
    ("ppa", "cf", "PPA-CF"),
    ("ppa", "gf", "PPA-GF"),
    ("pps", ANY, "PPS"),
    ("pps", "cf", "PPS-CF"),
    ("pva", ANY, "PVA"),
    ("tpu", ANY, "TPU"),
    ("tpu", "ams", "TPU-AMS"),
]

filament_options = {
    "vendor", "name", "version", "from", "is_custom_defined", "instantiation", "type",
    # https://github.com/bambulab/BambuStudio/blob/98bfabdd/src/libslic3r/Preset.cpp#L1853C30-L1857C30
    "compatible_prints", "compatible_prints_condition", "compatible_printers", "compatible_printers_condition",
    "inherits", "print_settings_id", "filament_settings_id", "sla_print_settings_id", "sla_material_settings_id",
    "printer_settings_id", "printer_model", "printer_variant", "default_print_profile", "default_filament_profile",
    "default_sla_print_profile", "default_sla_material_profile",
    # https://github.com/bambulab/BambuStudio/blob/98bfabdd/src/libslic3r/Preset.cpp#L857
    "default_filament_colour", "required_nozzle_HRC", "filament_diameter", "filament_type", "filament_soluble",
    "filament_is_support", "filament_scarf_seam_type", "filament_scarf_height", "filament_scarf_gap",
    "filament_scarf_length", "filament_max_volumetric_speed", "filament_flow_ratio", "filament_density",
    "filament_cost", "filament_minimal_purge_on_wipe_tower", "nozzle_temperature", "nozzle_temperature_initial_layer",
    "cool_plate_temp", "eng_plate_temp", "hot_plate_temp", "textured_plate_temp", "cool_plate_temp_initial_layer",
    "eng_plate_temp_initial_layer", "hot_plate_temp_initial_layer", "textured_plate_temp_initial_layer",
    "supertack_plate_temp_initial_layer", "supertack_plate_temp", "temperature_vitrification",
    "reduce_fan_stop_start_freq", "slow_down_for_layer_cooling", "fan_min_speed", "fan_max_speed",
    "enable_overhang_bridge_fan", "overhang_fan_speed", "overhang_fan_threshold",
    "overhang_threshold_participating_cooling", "close_fan_the_first_x_layers", "full_fan_speed_layer",
    "fan_cooling_layer_time", "slow_down_layer_time", "slow_down_min_speed", "filament_start_gcode",
    "filament_end_gcode", "activate_air_filtration", "during_print_exhaust_fan_speed",
    "complete_print_exhaust_fan_speed", "filament_retraction_length", "filament_z_hop", "filament_z_hop_types",
    "filament_retraction_speed", "filament_deretraction_speed", "filament_retract_restart_extra",
    "filament_retraction_minimum_travel", "filament_retract_when_changing_layer", "filament_wipe",
    "filament_retract_before_wipe", "filament_vendor", "compatible_prints", "compatible_prints_condition",
    "compatible_printers", "compatible_printers_condition", "inherits", "filament_wipe_distance",
    "additional_cooling_fan_speed", "nozzle_temperature_range_low", "nozzle_temperature_range_high",
    "enable_pressure_advance", "pressure_advance", "chamber_temperatures", "filament_notes",
    "filament_long_retractions_when_cut", "filament_retraction_distances_when_cut", "filament_shrink",
}


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


class Properties(BaseModel):
    adapter_url: Optional[str] = None
    bed_temp_max: Optional[int] = None
    bed_temp_min: Optional[int] = None
    fan_speed_max: Optional[int] = None
    fan_speed_min: Optional[int] = None
    flow_ratio: Union[float, int, None] = None
    k_value: Union[float, int, None] = None
    max_volumetric_speed: Union[float, int, None] = None
    softening_temp: Union[float, int, None] = None
    spool_count: Optional[int] = None
    spool_weight: Union[float, int, None] = None
    temp_max: Optional[int] = None
    temp_min: Optional[int] = None

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
    brand_key: str
    brand_name: str
    color: str
    created_at: str = Field(
        validation_alias=AliasChoices("created_at", "filament_created_at")
    )
    created_by: Optional[str] = None
    default_properties: Optional[Properties] = Field(None)
    default_website: Optional[str] = None
    deleted: Optional[str] = None
    id: int = Field(validation_alias=AliasChoices("id", "filament_id"))
    image: Optional[str] = None
    material: str
    material_key: str
    material_type: str
    material_type_key: str
    price_data: Union[PriceData, str, None] = None
    properties: Properties = Field(default_factory=Properties)
    rgb: Optional[str]
    short_code: Optional[str] = None
    spool_count: Optional[int] = None
    spool_weight: Union[float, int, None] = None
    td_value: Union[float, int, None] = None
    total_td_votes: Optional[int] = None
    updated_at: str = Field(
        validation_alias=AliasChoices("updated_at", "filament_updated_at")
    )
    updated_by: Optional[str] = None
    website: Optional[str] = None

    model_config = ConfigDict(strict=True, extra="ignore")

    def property_val(self, key: str) -> Any:
        if self.properties and getattr(self.properties, key, None) is not None:
            return getattr(self.properties, key)
        if self.default_properties:
            return getattr(self.default_properties, key)
        return None

    def to_bambu_lab_filament_format(self):
        for material_key, material_type_key, base_profile in reversed(base_profiles):
            if (
                self.material_key == material_key
                and self.material_type_key == material_type_key
            ):
                break
        else:
            base_profile = f"Generic {self.material_key.upper()}"
        if base_profile not in profiles_available:
            print(
                f"Warning: '{base_profile}.json' ({self.material} {self.material_type}) not in profiles",
                file=sys.stderr,
            )
            base_profile = ""  # fallback to inherits:""
        profile_name = " ".join(
            filter(None, [self.brand_name, self.material, self.material_type])
        )
        for material_key, material_type_key, filament_type in reversed(filament_types):
            if (
                self.material_key == material_key
                and self.material_type_key == material_type_key
            ):
                break
        else:
            filament_type = self.material_key.upper()
        if filament_type not in filament_types_available:
            print(
                f"Warning: '{filament_type}' ({self.material} {self.material_type}) not in filament_types",
                file=sys.stderr,
            )
            filament_type = ""  # fallback to filament_type:[]

        bambu_lab_filament_json = {
            "name": profile_name,
            "filament_type": [filament_type] if filament_type else [],
            "compatible_printers": [
                "Bambu Lab X1 Carbon 0.4 nozzle",
                "Bambu Lab X1 Carbon 0.6 nozzle",
                "Bambu Lab X1 Carbon 0.8 nozzle",
                "Bambu Lab P1S 0.4 nozzle",
                "Bambu Lab P1S 0.6 nozzle",
                "Bambu Lab P1S 0.8 nozzle",
                "Bambu Lab X1E 0.4 nozzle",
                "Bambu Lab X1E 0.6 nozzle",
                "Bambu Lab X1E 0.8 nozzle",
            ],
            "filament_settings_id": [profile_name],
            "inherits": base_profile,
            "from": "User",
            "is_custom_defined": "0",
            "filament_vendor": [self.brand_name],
            "version": bambu_studio_version,
        }
        if self.rgb is not None:
            bambu_lab_filament_json.update(
                {
                    "default_filament_colour": [self.rgb],
                }
            )
        temp_max = self.property_val("temp_max")
        temp_min = self.property_val("temp_min")
        if temp_max is not None or temp_min is not None:
            if temp_max is not None:
                bambu_lab_filament_json.update(
                    {
                        "nozzle_temperature_range_high": [f"{temp_max}"],
                    }
                )
            if temp_min is not None:
                bambu_lab_filament_json.update(
                    {
                        "nozzle_temperature_range_low": [f"{temp_min}"],
                    }
                )
        bed_temp_min = self.property_val("bed_temp_min")
        bed_temp_max = self.property_val("bed_temp_max")
        if bed_temp_min is not None or bed_temp_max is not None:
            # todo: better logic to determine best temp from range
            _temps = [bed_temp_min, bed_temp_max]
            temps = [temp for temp in _temps if temp is not None]
            best_temp: int = sum(temps) // len(temps)
            bambu_lab_filament_json.update(
                {
                    "hot_plate_temp": [f"{best_temp}"],
                    "hot_plate_temp_initial_layer": [f"{best_temp}"],
                    "textured_plate_temp": [f"{best_temp}"],
                    "textured_plate_temp_initial_layer": [f"{best_temp}"],
                    # "cool_plate_temp": [f"{best_temp}"],
                    # "cool_plate_temp_initial_layer": [f"{best_temp}"],
                    # "supertack_plate_temp": [f"{best_temp}"],
                    # "supertack_plate_temp_initial_layer": [f"{best_temp}"],
                }
            )
        softening_temp = self.property_val("softening_temp")
        if softening_temp is not None:
            bambu_lab_filament_json.update(
                {
                    "temperature_vitrification": [
                        f"{softening_temp:.2f}".rstrip("0").rstrip(".")
                    ],
                }
            )
        fan_speed_max = self.property_val("fan_speed_max")
        fan_speed_min = self.property_val("fan_speed_min")
        if fan_speed_max is not None or fan_speed_min is not None:
            if fan_speed_max is not None:
                bambu_lab_filament_json.update(
                    {
                        "fan_max_speed": [f"{fan_speed_max}"],
                    }
                )
            if fan_speed_min is not None:
                bambu_lab_filament_json.update(
                    {
                        "fan_min_speed": [f"{fan_speed_min}"],
                    }
                )
        flow_ratio = self.property_val("flow_ratio")
        if flow_ratio is not None:
            bambu_lab_filament_json.update(
                {
                    "filament_flow_ratio": [
                        f"{flow_ratio:.2f}".rstrip("0").rstrip(".")
                    ],
                }
            )
        max_volumetric_speed = self.property_val("max_volumetric_speed")
        if max_volumetric_speed is not None:
            bambu_lab_filament_json.update(
                {
                    "filament_max_volumetric_speed": [
                        f"{max_volumetric_speed:.2f}".rstrip("0").rstrip(".")
                    ],
                }
            )
        if getattr(self.price_data, "price", None):
            bambu_lab_filament_json.update(
                {
                    "filament_cost": [
                        f"{self.price_data.price:.2f}".rstrip("0").rstrip(".")
                    ],
                }
            )
        if self.td_value not in (None, 0) and self.total_td_votes not in (None, 0):
            bambu_lab_filament_json.update(
                {
                    "filament_retraction_minimum_travel": [
                        f"{self.td_value:.2f}".rstrip("0").rstrip(".")
                    ],
                }
            )
        # Unmapped fields:
        # color: str
        # props.k_value: Union[float, int, None]
        # props.spool_weight: Union[float, int, None]

        self.validate_bambu_lab_format(bambu_lab_filament_json)
        return bambu_lab_filament_json

    def validate_bambu_lab_format(self, data: dict):
        unknown_keys = set(data.keys()) - set(filament_options)
        if unknown_keys:
            raise ValueError(f"Unknown keys: {', '.join(unknown_keys)}")


class MyFilament(Filament):
    # Renamed fields
    filament_created_at: str = Field(
        alias="created_at",
        validation_alias=AliasChoices("created_at", "filament_created_at"),
    )
    created_at: str = Field(exclude=True)
    filament_id: int = Field(
        alias="id", validation_alias=AliasChoices("id", "filament_id")
    )
    id: int = Field(exclude=True)
    filament_updated_at: str = Field(
        alias="updated_at",
        validation_alias=AliasChoices("updated_at", "filament_updated_at"),
    )
    updated_at: str = Field(exclude=True)

    # Excluded fields
    short_code: Optional[str] = Field(exclude=True)

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
      "short_code": "2hYfZ5A9zscu",
      "brand_key": "123-3d",
      "material_key": "pla",
      "material_type_key": "basic",
      "brand_name": "123-3D",
      "material": "PLA",
      "material_type": "Basic",
      "color": "Zwart",
      "rgb": "#000000",
      "image": "/images/filaments/metallic_silver.jpg",
      "website": "https://www.123-3d.nl/123-3D-Filament-zwart-1-75-mm-PLA-1-1-kg-Jupiter-serie-i9729-t7316.html",
      "default_website": null,
      "price_data": {
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
      "properties": {
        "temp_max": 235,
        "temp_min": 195,
        "bed_temp_max": 75,
        "bed_temp_min": 55,
        "spool_weight": 216,
        "flow_ratio": 0.98
      },
      "default_properties": {
        "fan_speed_min": 90,
        "fan_speed_max": 100,
        "softening_temp": 190,
        "max_volumetric_speed": 12
      },
      "ASIN": null,
      "td_value": 2.5,
      "total_td_votes": 1,
      "deleted": null,
      "created_at": "2024-12-19T15:57:04.962+00:00",
      "created_by": "f8bc55a7-a4e9-4823-9cc9-d93fba5febc7",
      "updated_at": "2024-12-19T16:08:28.114+00:00",
      "updated_by": "f8bc55a7-a4e9-4823-9cc9-d93fba5febc7"
    }
    """

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "file", nargs="?", type=argparse.FileType("r"), help="path to a filaments.json"
    )
    parser.add_argument(
        "myfile",
        nargs="?",
        type=argparse.FileType("r"),
        help="path to a myfilaments.json",
    )
    parser.add_argument(
        "--test", action="store_true", help="Test models with data/filaments.json"
    )
    parser.add_argument(
        "--raw", action="store_true", help="Output raw json instead of bambu_lab format"
    )
    parser.add_argument(
        "--dir", help="Output directory (instead of stdout)"
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
        my_filaments = {
            filament["filament_id"]: filament
            for filament in json.load(args.myfile)["filaments"]
        }
    else:
        my_filaments = None
    results = {}
    for filament in filaments:
        if filament.get("filament_id", ""):
            # detected myfilament format in "filaments.json" file
            print(
                f'Error: Cannot load "myfilaments.json" without "filaments.json"! Try: {sys.argv[0]} path/to/filaments.json {args.file.name}',
                file=sys.stderr,
            )
            exit(1)
        validation_class = Filament
        if my_filaments:
            if filament["id"] not in my_filaments:
                continue
            validation_class = MyFilament
            extra = my_filaments[filament["id"]]
            filament.update(extra)
        try:
            f: Filament = validation_class.model_validate(filament)
            filename = os.path.join(
                "filaments",
                slugify(f.material_key).replace("-", "_"),
                slugify(f"{f.brand_key}-{f.material_key}-{f.material_type_key}") + "-BBL-filament.json",
            )
            results[filename] = (
                f.model_dump(mode="json")
                if args.raw
                else f.to_bambu_lab_filament_format()
            )
        except pydantic.ValidationError as e:
            print(e, file=sys.stderr)
            print(filament, file=sys.stderr)
            exit(1)

    if args.dir is None:
        # sort filename keys
        results = dict(sorted(results.items()))
        print(json.dumps(results, indent=2))
    else:
        shutil.rmtree(os.path.join(args.dir, "filaments"), ignore_errors=True)
        for filepath, data in results.items():
            new_file = os.path.join(args.dir, filepath)
            os.makedirs(os.path.dirname(new_file), exist_ok=True)
            with open(new_file, "w") as of:
                json.dump(data, of, indent=2)
