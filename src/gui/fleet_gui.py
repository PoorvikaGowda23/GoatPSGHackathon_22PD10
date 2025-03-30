import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json
import math
import logging
from typing import Tuple, Optional, Dict, List
from enum import Enum, auto
import time

# NavGraph class
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
        
        for vertex_data in level_data['vertices']:
            x, y, attributes = vertex_data
            name = attributes.get('name', '')
            is_charger = attributes.get('is_charger', False)
            self.vertices.append(Vertex(x, y, name, is_charger))
        
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
        if start_idx == end_idx:
            return [start_idx]
        
        distances = [float('inf')] * len(self.vertices)
        previous = [-1] * len(self.vertices)
        distances[start_idx] = 0
        unvisited = set(range(len(self.vertices)))
        
        while unvisited:
            current = min(unvisited, key=lambda x: distances[x])
            unvisited.remove(current)
            
            if current == end_idx:
                break
                
            for neighbor in self.get_adjacent_vertices(current):
                if neighbor in unvisited:
                    new_dist = distances[current] + 1
                    if new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        previous[neighbor] = current
        
        path = []
        current = end_idx
        while previous[current] != -1:
            path.append(current)
            current = previous[current]
        path.append(start_idx)
        path.reverse()
        
        return path if distances[end_idx] != float('inf') else []

# Robot class
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
        self.progress = 0.0
        self.current_lane: Optional[tuple] = None
        self.log = []
        self.battery = 100
        self.speed = 0.05
        self.waiting_since = None
        
    def get_color(self):
        if self.status == RobotStatus.MOVING:
            return "#0000FF"  # Blue
        elif self.status == RobotStatus.WAITING:
            return "#FF00FF"  # Magenta
        elif self.status == RobotStatus.IDLE:
            return "#00FF00"  # Green
        elif self.status == RobotStatus.CHARGING:
            return "#00FF00"  # Green (same as idle)
        elif self.status == RobotStatus.TASK_COMPLETE:
            return "#00FF00"  # Green (same as idle)
    
    def assign_task(self, destination_idx: int, nav_graph):
        if self.status == RobotStatus.CHARGING:
            return False, "Robot is currently charging"
        
        if self.current_vertex_idx is None:
            return False, "Robot has no current position"
            
        self.destination_vertex_idx = destination_idx
        self.path = nav_graph.find_shortest_path(self.current_vertex_idx, destination_idx)
        
        if not self.path:
            return False, "No valid path to destination"
            
        self.status = RobotStatus.MOVING
        self._move_to_next_vertex(nav_graph)
        self.log.append(f"Robot {self.id} assigned task to vertex {destination_idx}")
        return True, "Task assigned successfully"
    
    def _move_to_next_vertex(self, nav_graph):
        if len(self.path) < 2:
            self.status = RobotStatus.TASK_COMPLETE
            self.destination_vertex_idx = None
            return
            
        start_idx = self.path[0]
        end_idx = self.path[1]
        
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
            self.x = start_vertex.x + (end_vertex.x - start_vertex.x) * self.progress
            self.y = start_vertex.y + (end_vertex.y - start_vertex.y) * self.progress
        
        if self.status == RobotStatus.MOVING:
            self.battery = max(0, self.battery - 0.1)
            if self.battery < 20:
                chargers = [i for i, v in enumerate(nav_graph.vertices) if v.is_charger]
                if chargers:
                    nearest = min(chargers, key=lambda x: self._distance_to_vertex(nav_graph, x))
                    success, message = self.assign_task(nearest, nav_graph)
                    if success:
                        self.log.append(f"Robot {self.id} low battery, rerouting to charger at vertex {nearest}")
                    else:
                        self.log.append(f"Robot {self.id} failed to reroute to charger: {message}")
    
    def _distance_to_vertex(self, nav_graph, vertex_idx):
        vertex = nav_graph.vertices[vertex_idx]
        return ((self.x - vertex.x)**2 + (self.y - vertex.y)**2)**0.5
    
    def update_charging(self):
        if self.status == RobotStatus.CHARGING:
            self.battery = min(100, self.battery + 1)
            if self.battery >= 95:
                self.status = RobotStatus.IDLE
                self.log.append(f"Robot {self.id} finished charging")
    
    def update_waiting(self):
        if self.status == RobotStatus.WAITING:
            if self.waiting_since is None:
                self.waiting_since = time.time()
            elif time.time() - self.waiting_since > 5:  # 5 seconds timeout
                self.status = RobotStatus.IDLE
                self.waiting_since = None
                self.log.append(f"Robot {self.id} gave up waiting")

# FleetManager class
class FleetManager:
    def __init__(self, nav_graph: NavGraph):
        self.nav_graph = nav_graph
        self.robots: List[Robot] = []
        self.robot_id_counter = 1
        self.occupied_vertices: Dict[int, List[Robot]] = {}
        self.occupied_lanes: Dict[tuple, Robot] = {}
        self.conflicts: List[str] = []
        
        logging.basicConfig(
            filename='src/logs/fleet_logs.txt',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        self.logger = logging.getLogger('FleetManager')
    
    def reset_for_new_level(self):
        self.robots.clear()
        self.robot_id_counter = 1
        self.occupied_vertices.clear()
        self.occupied_lanes.clear()
        self.conflicts.clear()
    
    def spawn_robot(self, vertex_idx: int) -> Tuple[bool, str]:
        if vertex_idx < 0 or vertex_idx >= len(self.nav_graph.vertices):
            return False, "Invalid vertex index"
            
        if self.is_vertex_occupied(vertex_idx):
            return False, f"Vertex {vertex_idx} is already occupied"
            
        vertex = self.nav_graph.vertices[vertex_idx]
        robot = Robot(self.robot_id_counter, vertex.x, vertex.y)
        robot.current_vertex_idx = vertex_idx
        self.robots.append(robot)
        self.robot_id_counter += 1
        
        if vertex_idx not in self.occupied_vertices:
            self.occupied_vertices[vertex_idx] = []
        self.occupied_vertices[vertex_idx].append(robot)
        
        self.logger.info(f"Spawned robot {robot.id} at vertex {vertex_idx} ({vertex.name})")
        return True, f"Robot spawned successfully at vertex {vertex_idx}"
    
    def is_vertex_occupied(self, vertex_idx: int) -> bool:
        if vertex_idx not in self.occupied_vertices:
            return False
            
        vertex = self.nav_graph.vertices[vertex_idx]
        if vertex.is_charger:
            return False
            
        return len(self.occupied_vertices[vertex_idx]) > 0
    
    def assign_task(self, robot_id: int, destination_idx: int) -> Tuple[bool, str]:
        robot = next((r for r in self.robots if r.id == robot_id), None)
        if not robot or robot.current_vertex_idx is None:
            return False, "Robot not found or has no position"
            
        if destination_idx < 0 or destination_idx >= len(self.nav_graph.vertices):
            return False, "Invalid destination vertex"
            
        dest_vertex = self.nav_graph.vertices[destination_idx]
        if not dest_vertex.is_charger and self.is_vertex_occupied(destination_idx):
            conflict_msg = f"Vertex {destination_idx} is occupied by another robot"
            self.conflicts.append(conflict_msg)
            return False, conflict_msg
            
        success, message = robot.assign_task(destination_idx, self.nav_graph)
        if success:
            robot.status = RobotStatus.MOVING
        return success, message
    
    def update(self):
        self.occupied_vertices = {idx: [] for idx in range(len(self.nav_graph.vertices))}
        self.occupied_lanes.clear()
        self.conflicts.clear()
        
        for robot in self.robots:
            if robot.current_vertex_idx is not None and robot.current_vertex_idx >= len(self.nav_graph.vertices):
                robot.current_vertex_idx = None
                robot.status = RobotStatus.IDLE
                continue
                
            if robot.status == RobotStatus.CHARGING:
                robot.update_charging()
            elif robot.status == RobotStatus.WAITING:
                robot.update_waiting()
            elif robot.status == RobotStatus.MOVING:
                robot.update_position(self.nav_graph)
            
            if robot.current_vertex_idx is not None:
                self.occupied_vertices[robot.current_vertex_idx].append(robot)
        
        # Check for lane conflicts
        for robot in self.robots:
            if robot.status == RobotStatus.MOVING and robot.current_lane:
                lane_key = self.get_lane_key(robot.current_lane)
                if lane_key in self.occupied_lanes and self.occupied_lanes[lane_key] != robot:
                    other_robot = self.occupied_lanes[lane_key]
                    if other_robot.id < robot.id:  # Let lower ID robot have priority
                        robot.status = RobotStatus.WAITING
                        conflict_msg = f"Robot {robot.id} waiting for Robot {other_robot.id} on lane {lane_key}"
                        robot.log.append(conflict_msg)
                        self.conflicts.append(conflict_msg)
                    else:
                        other_robot.status = RobotStatus.WAITING
                        conflict_msg = f"Robot {other_robot.id} waiting for Robot {robot.id} on lane {lane_key}"
                        other_robot.log.append(conflict_msg)
                        self.conflicts.append(conflict_msg)
                else:
                    self.occupied_lanes[lane_key] = robot
        
        # Log all messages
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
            'color': robot.get_color()
        }
    
    def get_conflicts(self) -> List[str]:
        return self.conflicts

# FleetGUI class with enhanced notifications
class FleetGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fleet Management System")
        self.root.geometry("1400x800")
        
        self.nav_graph = NavGraph()
        self.fleet_manager = FleetManager(self.nav_graph)
        self.last_conflict_time = 0
        self.conflict_display_time = 3  # seconds
        
        try:
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent  # Go up to project root
            data_path = project_root / 'data' / 'nav_graph.json'
            
            if not data_path.exists():
                raise FileNotFoundError(f"Navigation graph file not found at {data_path}")
                
            self.nav_graph.load_from_json(str(data_path))
            self.available_levels = list(self.nav_graph.levels.keys())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load navigation graph: {str(e)}")
            self.root.destroy()
            return
        
        self.setup_ui()
        
        self.selected_robot = None
        self.selected_vertex = None
        self.animation_running = True
        self.update_interval = 100
        self.animation_speed = 1.0
        
        # Conflict notification label
        self.conflict_label = tk.Label(self.root, text="", fg="red", font=('Arial', 12, 'bold'))
        self.conflict_label.place(relx=0.5, rely=0.05, anchor=tk.CENTER)
        
        self.update()
    
    def setup_ui(self):
        self.root.grid_columnconfigure(0, weight=4)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(self.root, bg='white')
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        side_panel = ttk.Frame(self.root, width=300)
        side_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        side_panel.grid_propagate(False)
        
        side_panel.grid_rowconfigure(0, weight=1)
        side_panel.grid_rowconfigure(1, weight=1)
        side_panel.grid_rowconfigure(2, weight=1)
        side_panel.grid_rowconfigure(3, weight=4)
        side_panel.grid_columnconfigure(0, weight=1)
        
        level_frame = ttk.LabelFrame(side_panel, text="Level Selection", padding="2")
        level_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        self.setup_level_selector(level_frame)
        
        robot_info_frame = ttk.LabelFrame(side_panel, text="Robot Information", padding="3")
        robot_info_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 3))
        self.setup_robot_info(robot_info_frame)
        
        log_frame = ttk.LabelFrame(side_panel, text="Log", padding="3")
        log_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 3))
        self.setup_log_display(log_frame)
        
        control_frame = ttk.LabelFrame(side_panel, text="Controls", padding="5")
        control_frame.grid(row=3, column=0, sticky="nsew")
        self.setup_controls(control_frame)
        
        self.draw_nav_graph()
    
    def setup_level_selector(self, frame):
        frame.grid_columnconfigure(0, weight=1)
        self.level_var = tk.StringVar(value=self.nav_graph.current_level)
        level_menu = ttk.OptionMenu(frame, self.level_var, 
                                  self.nav_graph.current_level, 
                                  *self.available_levels,
                                  command=self.change_level)
        level_menu.grid(row=0, column=0, sticky="ew", padx=2, pady=1)
    
    def setup_robot_info(self, frame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.robot_info_text = tk.Text(frame, wrap=tk.WORD, height=3, font=('Arial', 9))
        self.robot_info_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.robot_info_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.robot_info_text['yscrollcommand'] = scrollbar.set
    
    def setup_log_display(self, frame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.log_text = tk.Text(frame, wrap=tk.WORD, height=4, font=('Arial', 8))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text['yscrollcommand'] = scrollbar.set
    
    def setup_controls(self, frame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        ttk.Button(frame, text="Spawn Robot", command=self.spawn_robot).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(frame, text="Assign Task", command=self.assign_task).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ttk.Button(frame, text="Pause/Resume", command=self.toggle_animation).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        ttk.Button(frame, text="Clear Logs", command=self.clear_logs).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
    
    def change_level(self, selected_level):
        try:
            self.nav_graph.load_level(selected_level)
            self.fleet_manager.reset_for_new_level()
            self.selected_robot = None
            self.selected_vertex = None
            self.draw_nav_graph()
            self.update_robot_info()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load level: {str(e)}")
    
    def draw_nav_graph(self):
        self.canvas.delete("all")
        
        # Draw lanes
        for lane in self.nav_graph.lanes:
            start = self.nav_graph.vertices[lane.start_idx]
            end = self.nav_graph.vertices[lane.end_idx]
            x1, y1 = self.to_canvas_coords(start.x, start.y)
            x2, y2 = self.to_canvas_coords(end.x, end.y)
            self.canvas.create_line(x1, y1, x2, y2, fill="gray", width=2)
        
        # Draw vertices
        for i, vertex in enumerate(self.nav_graph.vertices):
            x, y = self.to_canvas_coords(vertex.x, vertex.y)
            color = "#FFFF00" if vertex.is_charger else "#8B4513"  # Yellow for chargers, Brown for vertices
            radius = 10 if vertex.is_charger or vertex.name else 6
            outline = "red" if self.fleet_manager.is_vertex_occupied(i) else "black"
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, 
                                  fill=color, outline=outline, width=2, tags=f"vertex_{i}")
            if vertex.name:
                self.canvas.create_text(x, y-15, text=vertex.name, 
                                      fill="black", font=('Arial', 10, 'bold'))
    
    def to_canvas_coords(self, x: float, y: float) -> Tuple[int, int]:
        min_x = min(v.x for v in self.nav_graph.vertices)
        max_x = max(v.x for v in self.nav_graph.vertices)
        min_y = min(v.y for v in self.nav_graph.vertices)
        max_y = max(v.y for v in self.nav_graph.vertices)
        padding = 0.1 * max(max_x - min_x, max_y - min_y)
        min_x -= padding
        max_x += padding
        min_y -= padding
        max_y += padding
        
        canvas_width = self.canvas.winfo_width() or 1000
        canvas_height = self.canvas.winfo_height() or 600
        scaled_x = ((x - min_x) / (max_x - min_x)) * (canvas_width - 20) + 10
        scaled_y = ((y - min_y) / (max_y - min_y)) * (canvas_height - 20) + 10
        return int(scaled_x), int(scaled_y)
    
    def draw_robots(self):
        self.canvas.delete("robot")
        for robot in self.fleet_manager.robots:
            x, y = self.to_canvas_coords(robot.x, robot.y)
            radius = 10
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, 
                                  fill=robot.get_color(), outline="black", 
                                  tags=("robot", f"robot_{robot.id}"))
            self.canvas.create_text(x, y, text=str(robot.id), 
                                  tags=("robot", f"robot_{robot.id}"))
            if self.selected_robot == robot.id:
                self.canvas.create_oval(x-radius-3, y-radius-3, x+radius+3, y+radius+3,
                                      outline="red", width=2, 
                                      tags=("robot", f"robot_{robot.id}"))
    
    def on_canvas_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)
        
        robot_clicked = any(t.startswith("robot_") for t in tags)
        if robot_clicked:
            robot_id = int(next(t for t in tags if t.startswith("robot_")).split("_")[1])
            self.selected_robot = robot_id
            self.selected_vertex = None
            self.update_robot_info()
            return
        
        vertex_clicked = any(t.startswith("vertex_") for t in tags)
        if vertex_clicked:
            vertex_idx = int(next(t for t in tags if t.startswith("vertex_")).split("_")[1])
            if vertex_idx >= len(self.nav_graph.vertices):
                return
            self.selected_vertex = vertex_idx
            if self.selected_robot is None:
                self.spawn_robot(vertex_idx)
            else:
                self.assign_task(vertex_idx)
            return
        
        self.selected_robot = None
        self.selected_vertex = None
        self.update_robot_info()
    
    def spawn_robot(self, vertex_idx=None):
        if vertex_idx is None and self.selected_vertex is None:
            messagebox.showwarning("Warning", "Please select a vertex to spawn a robot")
            return
            
        idx = vertex_idx if vertex_idx is not None else self.selected_vertex
        if idx >= len(self.nav_graph.vertices):
            messagebox.showerror("Error", "Invalid vertex index")
            return
            
        success, message = self.fleet_manager.spawn_robot(idx)
        if success:
            messagebox.showinfo("Success", message)
            self.update_robot_info()
            self.draw_nav_graph()  # Redraw to show occupied vertex
        else:
            self.show_conflict(message)
    
    def assign_task(self, vertex_idx=None):
        if self.selected_robot is None:
            messagebox.showwarning("Warning", "Please select a robot first")
            return
            
        if vertex_idx is None and self.selected_vertex is None:
            messagebox.showwarning("Warning", "Please select a destination vertex")
            return
            
        dest_idx = vertex_idx if vertex_idx is not None else self.selected_vertex
        if dest_idx >= len(self.nav_graph.vertices):
            messagebox.showerror("Error", "Invalid destination vertex")
            return
            
        success, message = self.fleet_manager.assign_task(self.selected_robot, dest_idx)
        if success:
            messagebox.showinfo("Success", message)
        else:
            self.show_conflict(message)
        
        self.update_robot_info()
    
    def toggle_animation(self):
        self.animation_running = not self.animation_running
        if self.animation_running:
            self.update()
    
    def clear_logs(self):
        try:
            with open('src/logs/fleet_logs.txt', 'w') as f:
                pass
            self.log_text.delete(1.0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear logs: {str(e)}")
    
    def update_robot_info(self):
        self.robot_info_text.delete(1.0, tk.END)
        if self.selected_robot is None:
            self.robot_info_text.insert(tk.END, "No robot selected")
            return
            
        robot_info = self.fleet_manager.get_robot_info(self.selected_robot)
        if not robot_info:
            self.robot_info_text.insert(tk.END, f"Robot {self.selected_robot} not found")
            return
            
        info_str = f"Robot ID: {robot_info['id']}\n"
        info_str += f"Status: {robot_info['status']}\n"
        info_str += f"Battery: {robot_info['battery']:.1f}%\n"
        info_str += f"Position: ({robot_info['x']:.2f}, {robot_info['y']:.2f})\n"
        info_str += f"Current Vertex: {robot_info['current_vertex']}\n"
        info_str += f"Destination: {robot_info['destination'] if robot_info['destination'] is not None else 'None'}\n"
        self.robot_info_text.insert(tk.END, info_str)
    
    def update_log(self):
        try:
            with open('src/logs/fleet_logs.txt', 'r') as f:
                logs = f.readlines()
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, "".join(logs[-50:]))
        except FileNotFoundError:
            pass
    
    def show_conflict(self, message):
        """Show a conflict notification that disappears after a few seconds"""
        self.conflict_label.config(text=message)
        self.last_conflict_time = time.time()
        self.root.after(3000, self.clear_conflict_notification)
    
    def clear_conflict_notification(self):
        """Clear the conflict notification if it's old enough"""
        if time.time() - self.last_conflict_time >= self.conflict_display_time:
            self.conflict_label.config(text="")
    
    def update(self):
        if self.animation_running:
            self.fleet_manager.update()
            self.draw_nav_graph()
            self.draw_robots()
            self.update_robot_info()
            self.update_log()
            
            # Show any new conflicts
            conflicts = self.fleet_manager.get_conflicts()
            if conflicts and time.time() - self.last_conflict_time > self.conflict_display_time:
                self.show_conflict(conflicts[-1])
            
            delay = int(self.update_interval / self.animation_speed)
            self.root.after(delay, self.update)

def main():
    root = tk.Tk()
    app = FleetGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()