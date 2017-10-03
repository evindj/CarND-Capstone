#!/usr/bin/env python

import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
import tf

from styx_msgs.msg import TrafficLightArray, TrafficLight      #This is imported to test for traffic lights

import math

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 200 # Number of waypoints we will publish. You can change this number
Max_speed = 10  # Maximum speed (Miles per hour)
decel_distance=20  # the distance at which we start decelarating (m)


class WaypointUpdater(object):
	def __init__(self):
		rospy.init_node('waypoint_updater')

		rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
		self.base_waypoints_sub =rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

		# TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
		#****************************************************************************************************
		rospy.Subscriber('/traffic_waypoint',Int32,self.traffic_cb)                                   #*
		rospy.Subscriber('/obstacle_waypoint',Int32,self.obstacle_cb)
		#****************************************************************************************************


		self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

		# TODO: Add other member variables you need below
		#*****************************************************************************************
		self.next_wp_id=-1                                                     #*
		self.cur_pose=None
		self.all_waypoints=None
		#self.track_waypoints=None

		self.traffic_wp_id=-1
		self.obstacle_wp_id=-1
		self.too_close=False

	

		#*****************************************************************************************
		#self.publish()     # This publish the final waypoints with their speed for the car to follow
		self.publish()

        

	def pose_cb(self, msg):
		# TODO: Implement
		# Setting the current position of the car
		cur_position=Waypoint()
		cur_position.pose.header.frame_id =msg.header.frame_id
		cur_position.pose.header.stamp=msg.header.stamp
		cur_position.pose.pose=msg.pose
		self.cur_pose=cur_position
	
 
	def waypoints_cb(self, waypoints):
		# TODO: Implement
		if self.all_waypoints is None:
			self.all_waypoints = waypoints.waypoints
			self.base_waypoints_sub.unregister

	def traffic_cb(self, msg):
		# TODO: Callback for /traffic_waypoint message. Implement
		# setting the traffic waypoint id
		self.traffic_wp_id=msg.data

	def obstacle_cb(self, msg):
		# TODO: Callback for /obstacle_waypoint message. We will implement it later
		#setting the obstacle waypoint id 
		self.obstacle_wp_id=msg.data

	def get_waypoint_velocity(self, waypoint):
		return waypoint.twist.twist.linear.x

	def set_waypoint_velocity(self, waypoints, waypoint, velocity):
		waypoints[waypoint].twist.twist.linear.x = velocity

	'''def distance(self, waypoints, wp1, wp2):
		dist = 0
		dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
		for i in range(wp1, wp2+1):
			dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
			wp1 = i
		return dist'''
	def distance(self,waypoints,wp1,wp2):
		dist = 0
		dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
		for i in range(wp2-wp1):
			dist += dl(waypoints[wp1].pose.pose.position, waypoints[wp1+1].pose.pose.position)
			wp1 += 1
		return dist

	def get_closest_node_id(self):
		#car_pose=Waypoint()
		if self.cur_pose is None:
			return -1
        
		car_pose = self.cur_pose
		min_dist=float('inf')
		min_index=-1

		for i, waypoint in enumerate(self.all_waypoints):
			if(self.is_waypoint_ahead_of_car(car_pose,waypoint)):
				dist = self.distance([car_pose, waypoint],0,1)
				if dist < min_dist :
					min_dist=dist
					min_index=i

		return min_index


	def is_waypoint_ahead_of_car(self,ref_car,waypoint):
		quaternion =[ref_car.pose.pose.orientation.x,ref_car.pose.pose.orientation.y,ref_car.pose.pose.orientation.z,ref_car.pose.pose.orientation.w]
		roll,pitch,yaw = tf.transformations.euler_from_quaternion(quaternion)
		shift_x=waypoint.pose.pose.position.x - ref_car.pose.pose.position.x
		shift_y=waypoint.pose.pose.position.y - ref_car.pose.pose.position.y

		return (shift_x*math.cos(0-yaw)-shift_y*math.sin(0-yaw)) > 0



	def publish(self):
		rate=rospy.Rate(0.5)
		while not rospy.is_shutdown():

		# determining The closest waypoint in front of the car
        
			#track_waypoints=[]
			if self.all_waypoints is not None:


				self.next_wp_id=self.get_closest_node_id()
				if self.next_wp_id != -1:
					
					#if len(track_waypoints) != 0:
					#    track_waypoints[:]=[]
					#track_waypoints.extend(self.all_waypoints[self.next_wp_id:self.next_wp_id+LOOKAHEAD_WPS])
					track_waypoints=self.all_waypoints[self.next_wp_id:self.next_wp_id+LOOKAHEAD_WPS]
					if (self.traffic_wp_id != -1):
						dist = self.distance(track_waypoints,0,self.traffic_wp_id)
						if( dist <= decel_distance):
							self.too_close = True
						else:
							self.too_close=False

						#Setting the velocity of the waypoints
						if self.too_close is True:
							dist = self.distance(track_waypoints,0,self.traffic_wp_id)
							velocity=self.get_waypoint_velocity(track_waypoints[0])
							
							for i,waypoint in enumerate(track_waypoints[0:next_wp_id]):
								velocity -=velocity*self.distance(track_waypoints,0,i)/dist
								self.set_waypoint_velocity(track_waypoints,i,velocity)

						elif self.get_waypoint_velocity(track_waypoints[0]) < Max_speed :
							dist=20
							velocity=self.get_waypoint_velocity(track_waypoints[0])
							for i,waypoint in enumerate(track_waypoints):
								if(self.distance(track_waypoints,0,i) <= dist):
									velocity+=velocity*self.distance(track_waypoints,0,i)/dist
									self.set_waypoint_velocity(track_waypoints,i,velocity)
								else:
									self.set_waypoint_velocity(track_waypoints,i,Max_speed)

							
					

					if (self.traffic_wp_id == -1):
						velocity=self.get_waypoint_velocity(track_waypoints[0])
						if velocity <= Max_speed :
							dist=20
							velocity=self.get_waypoint_velocity(track_waypoints[0])
							for i,waypoint in enumerate(track_waypoints):
								if(self.distance(track_waypoints,0,i) <= dist):
									velocity+=velocity*self.distance(track_waypoints,0,i)/dist
									self.set_waypoint_velocity(track_waypoints,i,velocity)
								else:
									self.set_waypoint_velocity(track_waypoints,i,Max_speed)
						else:
							for i,waypoint in enumerate(track_waypoints):
								self.set_waypoint_velocity(track_waypoints,i,Max_speed)





					#self.traffic_wp_id =-1

					lane = Lane()
					lane.header.frame_id='/world'
					lane.header.stamp=rospy.Time(0)
					lane.waypoints = track_waypoints

					self.final_waypoints_pub.publish(lane)

					rospy.loginfo("Next position %s \n car position: %s", track_waypoints[0].pose.pose, self.cur_pose.pose.pose)
        
			rate.sleep()



if __name__ == '__main__':
	try:
		WaypointUpdater()
	except rospy.ROSInterruptException:
		rospy.logerr('Could not start waypoint updater node.')