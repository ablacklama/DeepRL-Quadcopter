import numpy as np
from gym import spaces
from geometry_msgs.msg import Vector3, Point, Quaternion, Pose, Twist, Wrench
from quad_controller_rl.tasks.base_task import BaseTask

class Land(BaseTask):
    """Simple task where the goal is to lift off the ground and reach a target height."""

    def __init__(self):
        # State space: <position_x, .._y, .._z, orientation_x, .._y, .._z, .._w>
        cube_size = 300.0  # env is cube_size x cube_size x cube_size

        self.observation_space = spaces.Box(
            np.array([- cube_size / 2, - cube_size / 2, 0.0,-1.0, -1.0, -1.0, -1.0]),
            np.array([  cube_size / 2,   cube_size / 2, cube_size,1.0, 1.0, 1.0, 1.0]))
        #print("Takeoff(): observation_space = {}".format(self.observation_space))  # [debug]

        # Action space: <force_x, .._y, .._z, torque_x, .._y, .._z>
        max_force = 25.0
        max_torque = 25.0

        self.action_space = spaces.Box(
            np.array([-max_force, -max_force, -max_force,-max_torque,-max_torque,-max_torque]),
            np.array([max_force, max_force, max_force,max_torque,max_torque,max_torque]))
        #print("Takeoff(): action_space = {}".format(self.action_space))  # [debug]

        # Task-specific parameters
        self.max_duration = 5.0  # secs
        self.target_pose_z = 0.0  # target height (z position) to reach for successful takeoff
        self.target_pose_x = 0.0
        self.target_pose_y = 0.0


        self.max_distance = 10.0

    def reset(self):
        # Nothing to reset; just return initial condition
        return Pose(
                position=Point(0.0, 0.0, np.random.normal(10, 1)),  # drop off from a random height
                orientation=Quaternion(0.0, 0.0, 0.0, 0.0),
            ), Twist(
                linear=Vector3(0.0, 0.0, 0.0),
                angular=Vector3(0.0, 0.0, 0.0)
            )
    

    def update(self, timestamp, pose, angular_velocity, linear_acceleration):
        # Prepare state vector (pose only; ignore angular_velocity, linear_acceleration)
        state = np.array([
            pose.position.x, pose.position.y, pose.position.z,
            pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w]).reshape(1, -1)
        # Compute reward / penalty and check if this episode is complete
        done = False

        error_position = - abs(self.target_pose_z - pose.position.z)  # Euclidean distance from target position vector
        acc_error = 5.0 * linear_acceleration.z
        reward = error_position + acc_error  # reward = zero for matching target z and stayed at x,y = 0,0

        #distance = np.sqrt(pose.position.x**2 + pose.position.y**2 + max(pose.position.z - 10, 0))
        #if distance > self.max_distance:
         #   reward -= 50.0  # extra penalty, agent strayed too far
          #  done = True
        #elif abs(pose.position.z) < .2:
         #   reward += 20.0  # extra reward, agent made it to the end
        if(timestamp > self.max_duration):
            done = True
        

        # Take one RL step, passing in current state and reward, and obtain action
        # Note: The reward passed in here is the result of past action(s)
        action = self.agent.step(state, reward, done)  # note: action = <force; torque> vector

        # Convert to proper force command (a Wrench object) and return it
        if action is not None:
            action = np.clip(action.flatten(), self.action_space.low, self.action_space.high)  # flatten, clamp to action space limits
            return Wrench(
                    force=Vector3(action[0], action[1], action[2]), 
                    torque=Vector3(action[3], action[4], action[5])),done
        else:
            return Wrench(), done
