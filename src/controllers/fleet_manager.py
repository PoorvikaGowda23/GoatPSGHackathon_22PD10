import json
from typing import List, Dict, Optional
from src.models.robot import Robot, RobotStatus
from src.models.nav_graph import NavGraph
import time
import logging
from enum import Enum

class FleetManager:
    def __init__(self, nav_graph: NavGraph):
        self.nav_graph = nav_graph
        self.robots: List[Robot] = []
        self.robot_id_counter = 1
        self.occupied_vertices: Dict[int, List[Robot]] = {}
        self.occupied_lanes: Dict[tuple, Robot] = {}
        
        logging.basicConfig(
            filename='src/logs/fleet_logs.txt',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        self.logger = logging.getLogger('FleetManager')
    
    def reset_for_new_level(self):
        """Reset fleet manager state for a new level"""
        self.robots.clear()
        self.robot_id_counter = 1
        self.occupied_vertices.clear()
        self.occupied_lanes.clear()
    
    def spawn_robot(self, vertex_idx: int) -> bool:
        if vertex_idx < 0 or vertex_idx >= len(self.nav_graph.vertices):
            return False
            
        if self.is_vertex_occupied(vertex_idx):
            return False
            
        vertex = self.nav_graph.vertices[vertex_idx]
        robot = Robot(self.robot_id_counter, vertex.x, vertex.y)
        robot.current_vertex_idx = vertex_idx
        self.robots.append(robot)
        self.robot_id_counter += 1
        
        if vertex_idx not in self.occupied_vertices:
            self.occupied_vertices[vertex_idx] = []
        self.occupied_vertices[vertex_idx].append(robot)
        
        self.logger.info(f"Spawned robot {robot.id} at vertex {vertex_idx} ({vertex.name})")
        return True
    
    def is_vertex_occupied(self, vertex_idx: int) -> bool:
        if vertex_idx not in self.occupied_vertices:
            return False
            
        vertex = self.nav_graph.vertices[vertex_idx]
        if vertex.is_charger:
            return False
            
        return len(self.occupied_vertices[vertex_idx]) > 0
    
    def assign_task(self, robot_id: int, destination_idx: int) -> bool:
        robot = next((r for r in self.robots if r.id == robot_id), None)
        if not robot or robot.current_vertex_idx is None:
            return False
            
        if destination_idx < 0 or destination_idx >= len(self.nav_graph.vertices):
            return False
            
        dest_vertex = self.nav_graph.vertices[destination_idx]
        if not dest_vertex.is_charger and self.is_vertex_occupied(destination_idx):
            return False
            
        success = robot.assign_task(destination_idx, self.nav_graph)
        if success:
            robot.status = RobotStatus.MOVING
        return success
    
    def update(self):
        # Initialize occupied_vertices for all vertices in current level
        self.occupied_vertices = {idx: [] for idx in range(len(self.nav_graph.vertices))}
        self.occupied_lanes.clear()
        
        # Update robot positions
        for robot in self.robots:
            if robot.current_vertex_idx >= len(self.nav_graph.vertices):
                robot.current_vertex_idx = None
                robot.status = RobotStatus.IDLE
                continue
                
            if robot.status == RobotStatus.CHARGING:
                robot.update_charging()
            elif robot.status in [RobotStatus.MOVING, RobotStatus.WAITING]:
                robot.update_position(self.nav_graph)
            
            if robot.current_vertex_idx is not None:
                self.occupied_vertices[robot.current_vertex_idx].append(robot)
        
        # Handle lane reservations
        for robot in self.robots:
            if robot.status == RobotStatus.MOVING and robot.current_lane:
                lane_key = self.get_lane_key(robot.current_lane)
                if lane_key in self.occupied_lanes and self.occupied_lanes[lane_key] != robot:
                    robot.status = RobotStatus.WAITING
                    robot.log.append(f"Robot {robot.id} waiting at lane {lane_key}")
                else:
                    self.occupied_lanes[lane_key] = robot
        
        # Log updates
        for robot in self.robots:
            for log_entry in robot.log:
                self.logger.info(log_entry)
            robot.log.clear()
    
    def get_lane_key(self, lane: tuple) -> tuple:
        return tuple(sorted(lane))
    
    def get_robot_info(self, robot_id: int) -> dict:
        robot = next((r for r in self.robots if r.id == robot_id), None)
        if not robot:
            return {}
            
        return {
            'id': robot.id,
            'x': robot.x,
            'y': robot.y,
            'status': robot.status.name,
            'battery': robot.battery,
            'destination': robot.destination_vertex_idx,
            'current_vertex': robot.current_vertex_idx,
            'color': robot.color
        }
    
    def get_all_robots_info(self) -> List[dict]:
        return [self.get_robot_info(robot.id) for robot in self.robots]