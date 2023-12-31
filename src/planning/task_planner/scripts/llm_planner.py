#!/usr/local/lib/robot_env/bin/python3

# ROS imports
import actionlib
import rospkg
import rospy
from std_srvs.srv import Trigger, TriggerResponse
from control_msgs.msg import FollowJointTrajectoryAction
from alfred_msgs.srv import GlobalTask, GlobalTaskResponse, VerbalResponse, VerbalResponseRequest, GlobalTaskRequest, UpdateParam, UpdateParamRequest, UpdateParamResponse
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal, MoveBaseActionResult, MoveBaseResult
from alfred_navigation.msg import NavManAction, NavManGoal
import os
import json
from task_planner.msg import PlanTriggerAction, PlanTriggerGoal, PlanTriggerResult, PlanTriggerFeedback
from manipulation.msg import PickTriggerGoal, PlaceTriggerGoal, PickTriggerAction, PlaceTriggerAction, PickTriggerResult, PlaceTriggerResult
from manipulation.msg import DrawerTriggerAction, DrawerTriggerFeedback, DrawerTriggerResult, DrawerTriggerGoal
from manipulation.msg import FindAlignAction, FindAlignResult, FindAlignGoal
from manipulation.msg import DeticRequestAction, DeticRequestGoal, DeticRequestResult

from vlmaps_ros.msg import VLMaps_primitiveAction, VLMaps_primitiveGoal, VLMaps_primitiveResult, VLMaps_primitiveFeedback
import numpy as np


class TaskPlanner:
    def __init__(self, test = True):
        rospy.init_node('task_planner')

        self.switch_to_manip_mode = rospy.ServiceProxy('/switch_to_manipulation_mode', Trigger)
        self.startNavService = rospy.ServiceProxy('/switch_to_navigation_mode', Trigger)

        self.navigation_client_old = actionlib.SimpleActionClient('move_base', MoveBaseAction)

        rospy.loginfo( "Waiting for driver services")
        self.stow_robot_service = rospy.ServiceProxy('/stow_robot', Trigger)
        self.stow_robot_service.wait_for_service()

        self.switch_to_manip_mode = rospy.ServiceProxy('/switch_to_manipulation_mode', Trigger)
        self.switch_to_manip_mode.wait_for_service()

        self.switch_to_nav_mode = rospy.ServiceProxy('/switch_to_navigation_mode', Trigger)
        self.switch_to_nav_mode.wait_for_service()

        self.trajectoryClient = actionlib.SimpleActionClient('alfred_controller/follow_joint_trajectory', FollowJointTrajectoryAction)
        self.trajectoryClient.wait_for_server()
        
        # # HRI Services
        
        rospy.loginfo( "Waiting for HRI services")
        self.tts_request_client = rospy.ServiceProxy('/interface/response_generator/verbal_response_service', VerbalResponse)
        self.tts_request_client.wait_for_service()
        
        self.update_param_service = rospy.ServiceProxy('/update_param', UpdateParam)
        self.update_param_service.wait_for_service()

        # NAVIGATION CLIENTS
        # TODO Replace with VLMAPS stuff.
        
        rospy.loginfo( "Waiting for navigation services")
        self.navigation_client = actionlib.SimpleActionClient('nav_man', NavManAction)
        self.navigation_client.wait_for_server()
        
        # MANIPULATION CLIENTS:
        rospy.loginfo("Waiting for manipulation services")
        self.pick_client = actionlib.SimpleActionClient('pick_action', PickTriggerAction)
        rospy.loginfo("Waiting for pick action server...")
        self.pick_client.wait_for_server()
        
        self.place_client = actionlib.SimpleActionClient('place_action', PlaceTriggerAction)
        rospy.loginfo("Waiting for place action server...")
        self.place_client.wait_for_server()
        
        self.drawer_client = actionlib.SimpleActionClient('drawer_action', DrawerTriggerAction)
        rospy.loginfo("Waiting for drawer action server...")
        self.drawer_client.wait_for_server()
        
        self.align_client = actionlib.SimpleActionClient('find_align_action', FindAlignAction)
        self.align_client.wait_for_server()
        
        rospy.loginfo("Waiting for DETIC services from scene_parser")
        self.detic_request_client = actionlib.SimpleActionClient('detic_request_scene_parser', DeticRequestAction)
        self.detic_request_client.wait_for_server()
        
        
        rospy.loginfo("Waiting for VLMAPS services")
        self.vlmaps_client = actionlib.SimpleActionClient('vlmaps_primitive_server', VLMaps_primitiveAction)
        self.vlmaps_client.wait_for_server()
        
        self.vlmaps_list = rospy.get_param('/vlmaps_brain/objects_list')
        self.class_list = rospy.get_param('/object_detection/class_list')
        self.server = actionlib.SimpleActionServer('task_planner', PlanTriggerAction, self.execute, False)
        self.server.start()
        
        self.drawer_location = None
        # - 'soda_can'
        # - 'tissue_paper'
        # - 'toothbrush'
        # - 'tie'
        # - 'cell phone'
        # - 'banana'
        # - 'apple'
        # - 'orange'
        # - 'bottle'
        # - 'cup'
        # - 'teddy_bear'
        # - 'remote'
        # - 'marker'
        # - 'table surface'

        rospy.loginfo( "Task planner ready to accept inputs...")

    def update_param(self, param_path, param_value):
        req = UpdateParamRequest(
            path = param_path,
            value = param_value
        )
        self.update_param_service(req)
    
    def execute(self, planGoal: PlanTriggerGoal):
        rospy.loginfo("Received plan")
        self.run_plan(planGoal.plan)
        result = PlanTriggerResult()
        
        success = True
        result.success = success
        result.index_at_failure = 0
        if success:
            self.server.set_succeeded(result)
        else:
            self.server.set_aborted(result)
    
    def pick(self, object_name):
        self.switch_to_manip_mode()
        
        natural_name = object_name.replace("_", " ")
        if object_name not in ['soda_can', 'tissue_paper']:
            object_name = natural_name
            
        objectId = self.class_list.index(object_name)

        self.speak("Picking " + natural_name, external=False)
        
        goal = PickTriggerGoal(
            objectId = objectId,
            use_planner = False
        )
        self.pick_client.send_goal(goal)
        self.pick_client.wait_for_result()
        result : PickTriggerResult = self.pick_client.get_result()
        return result.success
        
    def place(self, surface):
        self.switch_to_manip_mode()
        fixed_place = False
        use_place_location = False
        is_rotate = True
        place_location = []
        if surface == "drawer":
            self.speak("Placing inside drawer.", external=False)
            place_location = [
                0.0,
                -abs(self.drawer_location[2]) + 0.3,
                0.76 + 0.25
            ]
            fixed_place = False
            use_place_location = True
            is_rotate = False

        goal = PlaceTriggerGoal(
            place_location = place_location,
            fixed_place = fixed_place,
            use_place_location = use_place_location,
            is_rotate = is_rotate

        )
        self.place_client.send_goal(goal)
        self.place_client.wait_for_result()
        result : PlaceTriggerResult = self.place_client.get_result()
        return result.success
    
    def go_to(self, location):
        # self.primitives_mapping = {"go_to_object": self.go_to_object,
        #                     "move_between_objects": self.move_between_objects,
        #                     "move_object_closest_to": self.move_object_closest_to}

        self.update_param("visualization/active_primitive", f"go_to({location})")
        self.stow_robot_service()
        self.switch_to_nav_mode()
        natural_name = location.replace("_", " ")
        
        self.speak("Going to " + natural_name, external=False)

        if natural_name == "drawer":
            natural_name = 'potted plant'
        
        goal = VLMaps_primitiveGoal(
            primitive = "go_to_object",
            obj1 = natural_name,
            obj2 = "",
        )
        
        self.vlmaps_client.send_goal(goal)
        self.vlmaps_client.wait_for_result()
        result = self.vlmaps_client.get_result()
        return result.success
        
    
    def move_between_objects(self, loc1, loc2):
        self.update_param("visualization/active_primitive", f"go_between({loc1}, {loc2})")
        self.stow_robot_service()
        self.switch_to_nav_mode()
        natural_name_1 = loc1.replace("_", " ")
        natural_name_2 = loc2.replace("_", " ")
        self.speak("Moving between" + natural_name_1 + " and " + natural_name_2, external=False)
        if natural_name_1 == "drawer":
            natural_name_1 = "potted plant"
        if natural_name_2 == "drawer":
            natural_name_2 = "potted plant"
        goal = VLMaps_primitiveGoal(
            primitive = "move_between_objects",
            obj1 = natural_name_1,
            obj2 = natural_name_2,
        )
        
        self.vlmaps_client.send_goal(goal)
        self.vlmaps_client.wait_for_result()
        result = self.vlmaps_client.get_result()
        return result.success
    
    def move_object_closest_to(self, loc1, loc2):
        self.update_param("visualization/active_primitive", f"move_object_closest_to({loc1}, {loc2})")
        self.stow_robot_service()
        #move to obj1 that is closest to obj2
        self.switch_to_nav_mode()
        natural_name_1 = loc1.replace("_", " ")
        natural_name_2 = loc2.replace("_", " ")
        self.speak("Going to " + natural_name_1 + " closest to " + natural_name_2, external=False)
        
        if natural_name_1 == "drawer":
            natural_name_1 = "potted plant"
        if natural_name_2 == "drawer":
            natural_name_2 = "potted plant"
        goal = VLMaps_primitiveGoal(
            primitive = "move_object_closest_to",
            obj1 = natural_name_1,
            obj2 = natural_name_2,
        )
        
        self.vlmaps_client.send_goal(goal)
        self.vlmaps_client.wait_for_result()
        result = self.vlmaps_client.get_result()
        return result.success
    
    
    def find_and_align_to_object(self, object_name):
        self.update_param("visualization/active_primitive", f"find_and_align_to_object({object_name})")

        self.switch_to_manip_mode()
        # 3.39, 3.73
        natural_name = object_name.replace("_", " ")
        if object_name not in ['soda_can', 'tissue_paper']:
            object_name = natural_name
            
        objectId = self.class_list.index(object_name)
        self.speak("Searching for " + natural_name, external=False)
        
        goal = FindAlignGoal(
            objectId = objectId,
        )
        self.align_client.send_goal(goal)
        self.align_client.wait_for_result()
        result : FindAlignResult = self.align_client.get_result()
        return result.success
    
    def open_drawer(self):
        self.update_param("visualization/active_primitive", f"open_drawer()")
        self.switch_to_manip_mode()
        self.speak("Opening the drawer", external=False)
        goal = DrawerTriggerGoal(
            to_open = True,
            aruco_id = 0,
        )
        self.drawer_client.send_goal(goal)
        self.drawer_client.wait_for_result()
        result : DrawerTriggerResult = self.drawer_client.get_result()
        self.drawer_location = result.saved_position
        return result.success
        
            
    def close_drawer(self):
        self.update_param("visualization/active_primitive", f"close_drawer()")

        self.switch_to_manip_mode()
        self.speak("Closing the drawer", external=False)
        goal = DrawerTriggerGoal(
            to_open = False,
            aruco_id = 0,
        )
        self.drawer_client.send_goal(goal)
        self.drawer_client.wait_for_result()
        result : DrawerTriggerResult = self.drawer_client.get_result()
        return result.success
    
    def get_detections(self):
        self.update_param("visualization/active_primitive", f"get_detections()")

        self.detic_request_client.send_goal(DeticRequestGoal(request = True, get_surface = False))
        self.detic_request_client.wait_for_result()
        result : DeticRequestResult = self.detic_request_client.get_result()
        list_of_objects = result.list_of_objects

        if len(list_of_objects) == 0:
            strtospk = "I don't see anything."
        else:
            strtospk  = "I see "
            for i, obj in enumerate(list_of_objects):
                nat_name = obj.replace("_", " ")
                if i == len(list_of_objects) - 1:
                    strtospk += "and " + nat_name + "."
                else:
                    strtospk += nat_name + ", "

        self.speak(strtospk, external=False)

        return list_of_objects
    
    def speak(self, string_to_speak, external=True):
        if external:
            self.update_param("visualization/active_primitive", f"speak()")

        req = VerbalResponseRequest(
            response = string_to_speak
        )
        self.tts_request_client(req)
    
    def run_plan(self, plan):
        rospy.loginfo("Executing plan")
        
        plan += """\nexecute_plan(
            self.go_to, 
            self.move_between_objects, 
            self.move_object_closest_to, 
            self.pick, self.place, 
            self.open_drawer, 
            self.close_drawer, 
            self.find_and_align_to_object, 
            self.get_detections, 
            self.speak
        )
        """
        exec(plan)
        self.speak("task completed.", external=False)
        
        

if __name__ == "__main__":
    task_planner = TaskPlanner()
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("Shutting down")
    

