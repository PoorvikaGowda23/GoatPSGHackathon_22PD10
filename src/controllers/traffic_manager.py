from typing import Dict, List, Optional
from src.models.robot import Robot
from src.models.nav_graph import NavGraph

class TrafficManager:
    def __init__(self, nav_graph: NavGraph):
        self.nav_graph = nav_graph
        self.reservations: Dict[tuple, Robot] = {}  # (vertex_idx, time): robot
        self.intersection_queues: Dict[int, List[Robot]] = {}  # vertex_idx: [robots]
    
    def request_path(self, robot: Robot, path: List[int]) -> bool:
        """Check if path can be reserved without conflicts"""
        if not path:
            return False
            
        # Check each step in the path
        for i in range(len(path) - 1):
            current = path[i]
            next_vertex = path[i+1]
            
            # Check if the lane is available
            lane_key = (current, next_vertex) if current < next_vertex else (next_vertex, current)
            if lane_key in self.reservations and self.reservations[lane_key] != robot:
                return False
                
            # Check if the next vertex is available (unless it's the destination)
            if i < len(path) - 2:  # Not the last vertex in the path
                if next_vertex in self.intersection_queues and self.intersection_queues[next_vertex]:
                    return False
        
        # Reserve the path
        for i in range(len(path) - 1):
            current = path[i]
            next_vertex = path[i+1]
            lane_key = (current, next_vertex) if current < next_vertex else (next_vertex, current)
            self.reservations[lane_key] = robot
            
            if i < len(path) - 2:  # Not the last vertex in the path
                if next_vertex not in self.intersection_queues:
                    self.intersection_queues[next_vertex] = []
                self.intersection_queues[next_vertex].append(robot)
        
        return True
    
    def release_path(self, robot: Robot, path: List[int]):
        """Release reservations when robot completes its path"""
        for i in range(len(path) - 1):
            current = path[i]
            next_vertex = path[i+1]
            lane_key = (current, next_vertex) if current < next_vertex else (next_vertex, current)
            if lane_key in self.reservations and self.reservations[lane_key] == robot:
                del self.reservations[lane_key]
            
            if i < len(path) - 2:  # Not the last vertex in the path
                if next_vertex in self.intersection_queues and robot in self.intersection_queues[next_vertex]:
                    self.intersection_queues[next_vertex].remove(robot)
    
    def update(self):
        """Update traffic management state"""
        # Clear expired reservations (simplified - in real implementation would track time)
        pass