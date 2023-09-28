#!/usr/local/lib/robot_env/bin/python3

#
# Copyright (C) 2023 Auxilio Robotics
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

# ROS imports
import actionlib
from helpers import move_to_pose
import rospkg
import rospy
from std_srvs.srv import Trigger, TriggerResponse
from control_msgs.msg import FollowJointTrajectoryAction
from firebase_node import FirebaseNode


from alfred_msgs.msg import Speech, SpeechTrigger
from alfred_msgs.srv import GlobalTask, GlobalTaskResponse, VerbalResponse, VerbalResponseRequest, GlobalTaskRequest
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal, MoveBaseActionResult, MoveBaseResult
from manipulation.msg import TriggerAction, TriggerFeedback, TriggerResult, TriggerGoal

from state_manager import BotStateManager, Emotions, LocationOfInterest, GlobalStates, ObjectOfInterest, VerbalResponseStates, OperationModes
import os
import json
from enum import Enum
import pyrebase
import time

from utils import get_quaternion

class TaskPlanner:
    def __init__(self):
        rospy.init_node('task_planner')
        rospack = rospkg.RosPack()
        base_dir = rospack.get_path('task_planner')
        locations_file = rospy.get_param("locations_file", "config/locations.json")
        locations_path = os.path.join(base_dir, locations_file)
        self.goal_locations = json.load(open(locations_path))

        firebase_secrets_path = os.path.expanduser("~/firebasesecrets.json")
        if not os.path.isfile(firebase_secrets_path):
            raise FileNotFoundError("Firebase secrets file not found")
        
        with open(firebase_secrets_path, 'r') as f:
            config = json.load(f)

        with open(os.path.expanduser("~/alfred-autonomy/src/planning/task_planner/config/firebase_schema.json")) as f:
            self.state_dict = json.load(f)

        self.firebase = pyrebase.initialize_app(config)
        self.db = self.firebase.database()
        self.db.remove("")
        self.state_dict["button_callback"] = False
        self.db.set(self.state_dict) # fill
 
        self.last_update = time.time()

        self.bot_state = BotStateManager(self.stateUpdateCallback)



        rospack = rospkg.RosPack()
        self.startManipService = rospy.ServiceProxy('/switch_to_manipulation_mode', Trigger)
        self.startNavService = rospy.ServiceProxy('/switch_to_navigation_mode', Trigger)

        self.navigation_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        #self.commandReceived = rospy.Service('/robot_task_command', GlobalTask, self.command_callback)
        
        self.stow_robot_service = rospy.ServiceProxy('/stow_robot', Trigger)
        rospy.loginfo(f"[{rospy.get_name()}]:" + "Waiting for stow robot service...")
        # self.stow_robot_service.wait_for_service()

        rospy.loginfo(f"[{rospy.get_name()}]:" + "Waiting for move_base server...")
        self.navigation_client.wait_for_server()

        self.trajectoryClient = actionlib.SimpleActionClient('alfred_controller/follow_joint_trajectory', FollowJointTrajectoryAction)
        rospy.loginfo(f"[{rospy.get_name()}]:" + "Waiting for driver..")
        self.trajectoryClient.wait_for_server()


        self.task_requested = False
        self.time_since_last_command = rospy.Time.now()
        self.startManipService.wait_for_service()

        self.isManipMode = False
        self.runningTeleop = False

        self.mappings = {
            'fetch_water' : [LocationOfInterest.LIVING_ROOM, ObjectOfInterest.BOTTLE],
            'fetch_apple' : [LocationOfInterest.NET, ObjectOfInterest.APPLE],
            'fetch_remote' : [LocationOfInterest.LIVING_ROOM, ObjectOfInterest.REMOTE],
            'do_nothing' : [LocationOfInterest.LIVING_ROOM, ObjectOfInterest.NONE],
            'fetch_banana' : [LocationOfInterest.LIVING_ROOM, ObjectOfInterest.BANANA],
        }
        self.navigationGoal = None
        rospy.loginfo(f"[{rospy.get_name()}]:" + "Node Ready.")

        # create a timed callback to check if we have, Obj been idle for too long

    def stateUpdateCallback(self):
        
        if not self.bot_state.isAutonomous():
            if not self.isManipMode :
                self.isManipMode = True
                self.startManipService()
            
            if not self.runningTeleop:
                self.maintainvelocities()


    def main(self):
        while not rospy.is_shutdown():
            try:
                button_callback_value = self.db.child("button_callback").get().val()
                rospy.loginfo(button_callback_value)
                
                if button_callback_value == True:
                    navSuccess = self.executeTask()
                    if navSuccess == 1:
                        rospy.loginfo("Updating operation mode to video call")
                        self.bot_state.update_operation_mode(OperationModes.TELEOPERATION)
            except KeyboardInterrupt:
                rospy.loginfo("Keyboard interrupt received. Exiting the program.")

                # self.startNavService()
                # success = self.navigate_to_location(LocationOfInterest.TABLE)
                # self.bot_state.update_operation_mode(OperationModes.TELEOPERATION)
                # success = self.navigate_to_location(LocationOfInterest.HOME)

    def executeTask(self):

        # self.stow_robot_service()
        self.startNavService()
        navSuccess = self.navigate_to_location(self.navigationGoal)
        return navSuccess
        
    def navigate_to_location(self, location : Enum):
        #locationName = location.HOME
        #rospy.loginfo(f"[{rospy.get_name()}]:" +"Executing task. Going to {}".format(locationName))
        # send goal
        #print("Sending goal to move_base", self.goal_locations[locationName]['x'], self.goal_locations[locationName]['y'], self.goal_locations[locationName]['theta'])
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.pose.position.x = -3.32
        goal.target_pose.pose.position.y = -9.54
        quaternion = get_quaternion(240)
        goal.target_pose.pose.orientation = quaternion
        self.navigation_client.send_goal(goal, feedback_cb = self.bot_state.navigation_feedback)
        wait = self.navigation_client.wait_for_result()

        if self.navigation_client.get_state() != actionlib.GoalStatus.SUCCEEDED:
            rospy.loginfo(f"[{rospy.get_name()}]:" +"Failed to reach Table")
            # cancel navigation
            self.navigation_client.cancel_goal()
            return False
        
        rospy.loginfo(f"[{rospy.get_name()}]:" +"Reached Table")
        self.bot_state.update_emotion(Emotions.HAPPY)
        self.bot_state.update_state()
        self.bot_state.currentGlobalState = GlobalStates.REACHED_GOAL
        rospy.loginfo(f"[{rospy.get_name()}]:" +"Reached Table")
        return True


if __name__ == "__main__":
    task_planner = TaskPlanner()

    # rospy.sleep(2)
    try:
        #rospy.spin()
        task_planner.main()
    except KeyboardInterrupt:
        print("Shutting down")
    
    

