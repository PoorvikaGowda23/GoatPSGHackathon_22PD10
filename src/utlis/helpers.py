from typing import List, Tuple
import math

def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points"""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def interpolate_position(p1: Tuple[float, float], p2: Tuple[float, float], ratio: float) -> Tuple[float, float]:
    """Interpolate between two points based on ratio (0 to 1)"""
    return (
        p1[0] + (p2[0] - p1[0]) * ratio,
        p1[1] + (p2[1] - p1[1]) * ratio
    )

def path_length(path: List[Tuple[float, float]]) -> float:
    """Calculate total length of a path"""
    if len(path) < 2:
        return 0.0
    
    total = 0.0
    for i in range(len(path) - 1):
        total += calculate_distance(path[i], path[i+1])
    
    return total