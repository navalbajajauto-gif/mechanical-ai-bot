"""
calculators.py
Engineering calculators for CNC/VMC and production metrics.
All formulas are standard machining/production-engineering formulas.
Usage pattern (via Telegram): /rpm 100 20  ->  cutting_speed_m_min diameter_mm
"""

import math
from dataclasses import dataclass
from typing import List


class CalcError(Exception):
    pass


def _need(args: List[str], count: int, usage: str):
    if len(args) < count:
        raise CalcError(f"Kam arguments diye. Usage: {usage}")
    try:
        return [float(a) for a in args[:count]]
    except ValueError:
        raise CalcError(f"Numbers hi bhejo. Usage: {usage}")


def calc_rpm(args: List[str]) -> str:
    """N = (1000 * Vc) / (pi * D)  -- Vc in m/min, D in mm"""
    vc, d = _need(args, 2, "/rpm <cutting_speed_m/min> <diameter_mm>")
    if d