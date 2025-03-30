import json
from typing import Dict, List, Tuple, Optional

class Vertex:
    def __init__(self, x: float, y: float, name: str = "", is_charger: bool = False):
        self.x = x
        self.y = y
        self.name = name
        self.is_charger = is_charger

class Lane:
    def __init__(self, start_idx: int, end_idx: int, speed_limit: int = 0):
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.speed_limit = speed_limit

class NavGraph:
    def __init__(self):
        self.vertices: List[Vertex] = []
        self.lanes: List[Lane] = []
        self.levels: Dict[str, Dict[str, List]] = {}
        self.current_level = "level1"
        
    def load_from_json(self, file_path: str):
        with open(file_path, 'r') as f:
            data = json.load(f)
            self.levels = data['levels']
            self.load_level(self.current_level)
    
    def load_level(self, level_name: str):
        if level_name not in self.levels:
            raise ValueError(f"Level {level_name} not found in navigation graph")
        
        level_data = self.levels[level_name]
        self.vertices.clear()
        self.lanes.clear()
        
        # Load vertices
        for vertex_data in level_data['vertices']:
            x, y, attributes = vertex_data
            name = attributes.get('name', '')
            is_charger = attributes.get('is_charger', False)
            self.vertices.append(Vertex(x, y, name, is_charger))
        
        # Load lanes
        for lane_data in level_data['lanes']:
            start_idx, end_idx, attributes = lane_data
            speed_limit = attributes.get('speed_limit', 0)
            self.lanes.append(Lane(start_idx, end_idx, speed_limit))
    
    def get_vertex_by_name(self, name: str) -> Optional[Vertex]:
        for vertex in self.vertices:
            if vertex.name == name:
                return vertex
        return None
    
    def get_adjacent_vertices(self, vertex_idx: int) -> List[int]:
        adjacent = []
        for lane in self.lanes:
            if lane.start_idx == vertex_idx:
                adjacent.append(lane.end_idx)
            elif lane.end_idx == vertex_idx:
                adjacent.append(lane.start_idx)
        return adjacent
    
    def find_shortest_path(self, start_idx: int, end_idx: int) -> List[int]:
        """Find shortest path using Dijkstra's algorithm"""
        if start_idx == end_idx:
            return [start_idx]
        
        # Initialize distances and previous nodes
        distances = [float('inf')] * len(self.vertices)
        previous = [-1] * len(self.vertices)
        distances[start_idx] = 0
        unvisited = set(range(len(self.vertices)))
        
        while unvisited:
            # Find node with smallest distance
            current = min(unvisited, key=lambda x: distances[x])
            unvisited.remove(current)
            
            # Stop if we've reached the destination
            if current == end_idx:
                break
                
            # Update distances for neighbors
            for neighbor in self.get_adjacent_vertices(current):
                if neighbor in unvisited:
                    new_dist = distances[current] + 1  # All edges have equal weight
                    if new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        previous[neighbor] = current
        
        # Reconstruct path
        path = []
        current = end_idx
        while previous[current] != -1:
            path.append(current)
            current = previous[current]
        path.append(start_idx)
        path.reverse()
        
        return path if distances[end_idx] != float('inf') else []