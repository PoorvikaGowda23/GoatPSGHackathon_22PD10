from enum import Enum, auto
from typing import List, Optional
import time
import random

class RobotStatus(Enum):
    IDLE = auto()
    MOVING = auto()
    WAITING = auto()
    CHARGING = auto()
    TASK_COMPLETE = auto()

class Robot:
    def __init__(self, robot_id: int, x: float, y: float):
        self.id = robot_id
        self.x = x
        self.y = y
        self.status = RobotStatus.IDLE
        self.current_vertex_idx: Optional[int] = None
        self.destination_vertex_idx: Optional[int] = None
        self.path: List[int] = []
        self.progress = 0.0  # Progress along current lane (0 to 1)
        self.current_lane: Optional[tuple] = None
        self.color = self._generate_color()
        self.log = []
        self.battery = 100
        self.speed = 0.05  # Movement speed (progress per update)
        
    def _generate_color(self):
        # Generate a random but consistent color based on robot ID
        random.seed(self.id)
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))
    
    def assign_task(self, destination_idx: int, nav_graph):
        if self.status == RobotStatus.CHARGING:
            return False
        
        if self.current_vertex_idx is None:
            return False
            
        self.destination_vertex_idx = destination_idx
        self.path = nav_graph.find_shortest_path(self.current_vertex_idx, destination_idx)
        
        if not self.path:
            return False
            
        self.status = RobotStatus.MOVING
        self._move_to_next_vertex(nav_graph)
        self.log.append(f"Robot {self.id} assigned task to vertex {destination_idx}")
        return True
    
    def _move_to_next_vertex(self, nav_graph):
        if len(self.path) < 2:
            self.status = RobotStatus.TASK_COMPLETE
            self.destination_vertex_idx = None
            return
            
        start_idx = self.path[0]
        end_idx = self.path[1]
        
        # Find the lane that connects these vertices
        for lane in nav_graph.lanes:
            if (lane.start_idx == start_idx and lane.end_idx == end_idx) or \
               (lane.end_idx == start_idx and lane.start_idx == end_idx):
                self.current_lane = (start_idx, end_idx)
                break
        
        self.progress = 0.0
        self.current_vertex_idx = start_idx
        self.path.pop(0)
    
    def update_position(self, nav_graph):
        if self.status != RobotStatus.MOVING:
            return
            
        if not self.current_lane:
            self._move_to_next_vertex(nav_graph)
            return
            
        start_idx, end_idx = self.current_lane
        start_vertex = nav_graph.vertices[start_idx]
        end_vertex = nav_graph.vertices[end_idx]
        
        self.progress += self.speed
        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_vertex_idx = end_idx
            self.x = end_vertex.x
            self.y = end_vertex.y
            
            if end_vertex.is_charger and self.battery < 50:
                self.status = RobotStatus.CHARGING
                self.log.append(f"Robot {self.id} started charging at vertex {end_idx}")
            elif not self.path:
                self.status = RobotStatus.TASK_COMPLETE
                self.log.append(f"Robot {self.id} completed task at vertex {end_idx}")
            else:
                self._move_to_next_vertex(nav_graph)
        else:
            # Interpolate position
            self.x = start_vertex.x + (end_vertex.x - start_vertex.x) * self.progress
            self.y = start_vertex.y + (end_vertex.y - start_vertex.y) * self.progress
        
        # Battery consumption
        if self.status == RobotStatus.MOVING:
            self.battery = max(0, self.battery - 0.1)
            if self.battery < 20:
                # Find nearest charger
                chargers = [i for i, v in enumerate(nav_graph.vertices) if v.is_charger]
                if chargers:
                    nearest = min(chargers, key=lambda x: self._distance_to_vertex(nav_graph, x))
                    self.assign_task(nearest, nav_graph)
                    self.log.append(f"Robot {self.id} low battery, rerouting to charger at vertex {nearest}")
    
    def _distance_to_vertex(self, nav_graph, vertex_idx):
        vertex = nav_graph.vertices[vertex_idx]
        return ((self.x - vertex.x)**2 + (self.y - vertex.y)**2)**0.5
    
    def update_charging(self):
        if self.status == RobotStatus.CHARGING:
            self.battery = min(100, self.battery + 1)
            if self.battery >= 95:
                self.status = RobotStatus.IDLE
                self.log.append(f"Robot {self.id} finished charging")