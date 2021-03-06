#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import logging
import configpi

from louie import dispatcher
from datetime import datetime
from flask import jsonify
from collections import OrderedDict

from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('openzwave')

started = False
name = configpi.name






###########################################################################################################################
###########################################################################################################################
##########    Root parent backend class     ###############################################################################
###########################################################################################################################
###########################################################################################################################


class Backend():

    def __init__(self):

	###################  instanciation de l'objet backend ########################################################


	###### options needed for python openzwave library like config files path, logging, 
        device = configpi.interface
        options = ZWaveOption(device, config_path="/home/hepia/IoTLab/python-openzwave/openzwave/config", user_path=".", cmd_line="")
        options.set_log_file("OZW.log")
        options.set_append_log_file(False)
        options.set_console_output(False)
        options.set_save_log_level('Warning')
        options.set_logging(True)
        options.lock()

        # creation of the object network using the options entity already created
        self.network = ZWaveNetwork(options, autostart=False)

	###### 	 These dispatchers associate a method to a signal. the signals are generated by the library python-openzwave.
	######   Once the signal is received. It's associated method is executed (see "_node_added" example below in "_network_started" method)
        dispatcher.connect(self._network_started, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
        dispatcher.connect(self._network_ready, ZWaveNetwork.SIGNAL_NETWORK_READY)

	###### backend object attributes
#        self.devices = OrderedDict()  ### will contain the list of nodes in the network
#        self.sensors = OrderedDict()  ### will contain the list of sensors (only) in the network
        self.node_added = False
        self.node_removed = False
        self.timestamps = {}	      ### will contain the time of the last values' update for each sensor
        self.queryStages = {	      ### the diffrent stages that a node object gets through before being ready 
                "None"                  :  1, # Query process hasn't started for this node
                "ProtocolInfo"          :  2, # Retrieve protocol information
                "Probe"                 :  3, # Ping device to see if alive
                "WakeUp"                :  4, # Start wake up process if a sleeping node
                "ManufacturerSpecific1" :  5, # Retrieve manufacturer name and product ids if ProtocolInfo lets us
                "NodeInfo"              :  6, # Retrieve info about supported, controlled command classes
                "SecurityReport"        :  7, # Retrieve a list of Command Classes that require Security
                "ManufacturerSpecific2" :  8, # Retrieve manufacturer name and product ids
                "Versions"              :  9, # Retrieve version information
                "Instances"             : 10, # Retrieve information about multiple command class instances
                "Static"                : 11, # Retrieve static information (doesn't change)
                "Probe1"                : 12, # Ping a device upon starting with configuration
                "Associations"          : 13, # Retrieve information about associations
                "Neighbors"             : 14, # Retrieve node neighbor list
                "Session"               : 15, # Retrieve session information (changes infrequently)
                "Dynamic"               : 16, # Retrieve dynamic information (changes frequently)
                "Configuration"         : 17, # Retrieve configurable parameter information (only done on request)
                "Complete"              : 18  # Query process is completed for this node
        }

#######################################################################################################################
############# LAUNCH  #################################################################################################
#######################################################################################################################

    def _network_started(self, network):

	# executed once the software representation is started. the discovery of the network components has begun. they will be mapped into objects

        print("network started - %d nodes were found." % network.nodes_count)

	# these dispatchers associate a method to a signal. the signals are generated by the library python-openzwave.
	# a signal may contain a number of parameters that are passed to the method associated to the signal.
	# for exemple, the dispatcher below associates the signal "SIGNAL_NODE_ADDED" to the method "_node_added" that is implemented below (line 111).
	# the signal "SIGNAL_NODE_ADDED" transports two parameters which are the objects network and node.
	# once this signal is received, these two parameters will be passed to the method "_node_added" and the method will be executed.

        dispatcher.connect(self._node_added, ZWaveNetwork.SIGNAL_NODE_ADDED)
        dispatcher.connect(self._node_removed, ZWaveNetwork.SIGNAL_NODE_REMOVED)


        

    def _network_ready(self, network):

	# executed once the software representation is ready

        print("network : ready : %d nodes were found." % network.nodes_count)
        print("network : controller is : %s" % network.controller)
        dispatcher.connect(self._value_update, ZWaveNetwork.SIGNAL_VALUE)

    def _node_added(self, network, node):

	# executed when node is added to the software representation. it's executed after the method "_debug_node_new" (see below)

        print('node added: %s.' % node.node_id)
        self.timestamps["timestamp" + str(node.node_id)] = "None"
        self.node_added = True

    def _node_removed(self, network, node):

	# executed when node is removed from the software representation

        print('node removed: %s.' % node.name)
        self.node_removed = True


    def _value_update(self, network, node, value):

	# executed when a new value from a node is received

        print('Node %s: value update: %s is %s.' % (node.node_id, value.label, value.data))
        self.timestamps["timestamp" + str(node.node_id)] = int(time.time())




################################################################################################################
######################## START AND STOP THE SOFTWARE REPRESENTATION ############################################
################################################################################################################

    def start(self):

	# this method starts the software representation
        global started


        if started:
            print "Already started"
            return 
        started = True
        self.network.start()
        print "Z-Wave Network Starting..."
        for i in range(0, 300):
            if self.network.state == self.network.STATE_READY:
                break
            else:
                time.sleep(1.0)
        if not self.network.is_ready:
            print "Network is not ready but continue anyway"
        print "------------------------------------------------------------"
        print "Nodes in network : %s" % self.network.nodes_count
        print "------------------------------------------------------------"
            
    def stop(self):

	# this method stops the software representation

        global started
	started = False
        print "Stopping Z-Wave Network... "
        self.network.stop()
        
    def reset(self):
        if self.network.nodes_count == 1:
            self.network.controller.hard_reset()
            return "Hard Reset Done"
        return "Cannot make Hard Reset while nodes included in network"


#######################################################################################################################
############# NETWORK #################################################################################################
#######################################################################################################################

        
        
    def network_info(self):

        # this method returns a JSON that lists all network nodes and gives some informations about each one of them like the ID, neighbors, ...

        result = {}
        result ['Network Home ID'] = self.network.home_id_str    

        for node in self.ordered_nodes_dict().itervalues():
#                result ['Node ID'] = "Node "+str(node.node_id)
                info = {}
                info ['Node ID'] = str(node.node_id)
                info ['Node name'] = str(node.name)
                info ['Node location'] = str(node.location)
                info ['Product name'] = str(node.product_name)
                info ['Is Ready'] = node.isReady
                info ['Query Stage'] = node.getNodeQueryStage
                info ['Query Stage (%)'] = str(self.queryStages[node.getNodeQueryStage]*100/18)+" %"
                info ['Neighbours'] = ", ".join(str(s) for s in node.neighbors)
                result ['Node '+str(node.node_id)] = info
        return jsonify(result)



#######################################################################################################################
############# NODES #################################################################################################
#######################################################################################################################   


    def ordered_nodes_dict(self):
    
    # returns an ordered list of the network's nodes sorted by node's id

        return OrderedDict(sorted(self.network.nodes.items()))


    def addNode(self):

    #  passes the controller to inclusion mode and gets it out of it after 20 seconds 

        if self.network.state < self.network.STATE_STARTED:
            return "Network not started"
        self.node_added = False
        result = self.network.controller.begin_command_add_device()
        if result == True:
            for x in range(1, 21):
                time.sleep(1)
                if x%2 == 0:
                    sys.stdout.write("+")
                    sys.stdout.flush()
                if x == 20:
                    sys.stdout.write(" ! ")
                    sys.stdout.flush()
                    self.network.controller.cancel_command()
                    return "Too long to add a node ! Max. 20 seconds"
                if self.node_added == True:
                    self.node_added = False
                    return "Added node success"
        return "Added node failed \n"


    def removeNode(self):

    #  passes the controller to exclusion mode and gets it out of it after 20 seconds 

        if self.network.state < self.network.STATE_STARTED:
            return "Network not started"
        self.node_removed = False
        result = self.network.controller.begin_command_remove_device()
        if result == True:
            for x in range(1, 21):
                time.sleep(1)
                if x%2 == 0:
                    sys.stdout.write("-")
                    sys.stdout.flush()
                if x == 20:
                    sys.stdout.write(" ! ")
                    sys.stdout.flush()
                    self.network.controller.cancel_command()
                    return "Too long to remove a node ! Max. 20 seconds"
                if self.node_removed == True:
                    self.node_removed = False
                    return "Removed node success"
        return "Removed node failed \n"
   
    def get_nodes_list(self):

    # returns the list of nodes 
        nodes = OrderedDict()
        for node in self.ordered_nodes_dict().iterkeys():
            #print("Node %d" % node.node_id)
            #print("Product name %s" % node.product_name)
            if self.network.nodes[node].isReady:
                nodes[str(node)] = self.network.nodes[node].product_name
            else:
                nodes[str(node)] = ""
        return jsonify(nodes)

    def set_node_location(self, n, value):
        for node in self.network.nodes.itervalues():
            if node.node_id == n :
                temp = node.location
                node.location = value
                return "Node location updated from "+temp+" to "+value
        return "Node not found"

    def set_node_name(self, n, value):
        for node in self.network.nodes.itervalues():
            if node.node_id == n :
                temp = node.name
                node.name=value
                return "Node name updated from "+temp+" to "+value
        return "Node not found"        

    def get_node_location(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n :
                temp = node.location
                return "Node location is "+temp
        return "Node not found"

    def get_node_name(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n :
                temp = node.name
                return "Node name is "+temp
        return "Node not found"

    def get_neighbours_list(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n :
                temp = ", ".join(str(s) for s in node.neighbors)
                return " neighbors of the node "+str(n)+" by ID are : "+temp+" ."
        return "Node not found"

    def set_node_config_parameter(self, n, param, value, size):

    # sets a configuration parameter to a given value

        for node in self.network.nodes.itervalues():
            if node.node_id == n:
                node.set_config_param(param, value, size)
        return "Value for param " + str(param) + " is now " + str(value)

    def get_node_config_parameter(self, n, param):

     # gets the value of a configuration parameter

        for node in self.network.nodes.itervalues():
            if node.node_id == n:
                node.request_config_param(param)
                values = node.get_values("All","Config","All",False,"All")
                for value in values.itervalues():
                    if value.index == param:
                        return "Value for param " + str(param) + " is " + str(value.data)
        return "Get config param failed"


    def get_nodes_Configuration(self):

        # this method returns a JSON that gives an overview of the network and it's nodes' configuration parameters (like the ID, Wake-up Interval, Group 1 Reports, Group 1 Interval ...)


        result = {}
        result ['Network Home ID'] = self.network.home_id_str
        for node in self.ordered_nodes_dict().itervalues():
            if node.isReady and node.node_id is not 1:
                node.request_all_config_params()                      # Update of the software representation: retreive the last status of the Z-Wave network
                values = node.get_values("All","All","All",False,"All") # Get Config + System values 
                nodeValues = {}
                for value in values.itervalues():
                    nodeValues[value.label] = value.data
                    #nodeValues[int(value.index)] = value.data
                    #print str(value.index)+"  "+str(value.label)+" "+str(value.data)+" id:"+str(node.node_id)
                #info = {}
                #info ['Node ID']                = str(node.node_id)
                #info ['Wake-up Interval']       = str(nodeValues[0])
                #info ['Enable Motion Sensor']   = str(nodeValues[4])
                #info ['Group 1 Reports']        = str(nodeValues[101])
                #info ['Group 1 Interval']       = str(nodeValues[111])
                #info ['Group 2 Reports']        = str(nodeValues[102])
                #info ['Group 2 Interval']       = str(nodeValues[112])
                #info ['Group 3 Reports']        = str(nodeValues[103])
                #info ['Group 3 Interval']       = str(nodeValues[113])
                
                result ['Node '+str(node.node_id)] =  nodeValues
        return jsonify(result)


    

#######################################################################################################################
############# Multisensors #################################################################################################
#######################################################################################################################        

class Backend_with_sensors(Backend):

    def get_sensors_list(self):

	# returns the list of sensors
	sensors = OrderedDict()
        for node in self.ordered_nodes_dict().iterkeys():
            if self.network.nodes[node].get_sensors():
                if self.network.nodes[node].isReady:
                    sensors[str(node)] = self.network.nodes[node].product_name
                else:
                    sensors[str(node)] = ""
        return jsonify(sensors)
    

    def get_temperature(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp"+str(node.node_id) in self.timestamps:
                values = node.get_values(0x31, "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Temperature":
                        val = round(value.data,1)
                #        if len(node.location) < 3:
                #            node.location = configpi.sensors[str(node.node_id)][:4]
                        return jsonify(controller = name, sensor = node.node_id, location = node.location, type = value.label.lower(), updateTime = self.timestamps["timestamp"+str(node.node_id)], value = val)
        return "Node not ready or wrong sensor node !"						

    def get_humidity(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp"+str(node.node_id) in self.timestamps:
                values = node.get_values(0x31, "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Relative Humidity":
                        val = int(value.data)
                 #       if len(node.location) < 3:
                 #           node.location = configpi.sensors[str(node.node_id)][:4]
                        return jsonify(controller = name, sensor = node.node_id, location = node.location, type = value.label.lower(), updateTime = self.timestamps["timestamp"+str(node.node_id)], value = val)
        return "Node not ready or wrong sensor node !"

    def get_luminance(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp"+str(node.node_id) in self.timestamps:
                values = node.get_values(0x31, "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Luminance":
                        val = int(value.data)
                #        if len(node.location) < 3:
                #            node.location = configpi.sensors[str(node.node_id)][:4]
                        return jsonify(controller = name, sensor = node.node_id, location = node.location, type = value.label.lower(), updateTime = self.timestamps["timestamp"+str(node.node_id)], value = val)
        return "Node not ready or wrong sensor node !"

    def get_motion(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp"+str(node.node_id) in self.timestamps:
                values = node.get_values(0x30, "User", "All", True, False)
                for value in values.itervalues():
                    if value.label == "Sensor":
                        val = value.data
                #        if len(node.location) < 3:
                #            node.location = configpi.sensors[str(node.node_id)][:4]
                        return jsonify(controller = name, sensor = node.node_id, location = node.location, type = value.label.lower(), updateTime = self.timestamps["timestamp"+str(node.node_id)], value = val)        
        return "Node not ready or wrong sensor node !"

    def get_battery(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp"+str(node.node_id) in self.timestamps:
                val = node.get_battery_level()
                return jsonify(controller = name, sensor = node.node_id, location = node.location, type = "battery", updateTime = self.timestamps["timestamp"+str(node.node_id)], value = val)
        return "Node not ready or wrong sensor node !"


    def get_all_Measures(self, n):
        for node in self.network.nodes.itervalues():
            if node.node_id == n and node.isReady and n != 1 and "timestamp"+str(node.node_id) in self.timestamps:
                values = node.get_values("All", "User", "All", True, False)
              #  if len(node.location) < 3:
              #      node.location = configpi.sensors[str(node.node_id)][:4]
                measures = {}
                measures['controller'] = name
                measures['sensor'] = node.node_id
                measures['location'] = str(node.location)
                measures['updateTime'] = self.timestamps["timestamp"+str(node.node_id)]
                for value in values.itervalues():
                    if value.label == "Battery Level":
                        measures["battery"] = value.data
                    if value.label == "Sensor":
                        measures["motion"] = value.data
                    if value.label == "Temperature":
                        measures[value.label.lower()] = round(value.data, 1)
                    if value.label == "Relative Humidity":
                        measures[value.label.lower()[9:]] = int(value.data)
                    if value.label == "Luminance":
                        measures[value.label.lower()] = int(value.data)
                    if value.label == "Ultraviolet":                       # U V (new sensors)
                        measures[value.label.lower()] = int(value.data)
                    if value.label == "Burglar":                           # Vibration (new sensors)
                        measures[value.label.lower()] = int(value.data)
                return jsonify(measures)
        return "Node not ready or wrong sensor node type !"


    def set_basic_sensor_nodes_configuration(self, Grp_interval, Grp_reports, Wakeup_interval):

    # this method configures the nodes whith a specific configuration

        if self.network.state < self.network.STATE_STARTED:
            return "Network Not Started"
        for node in self.ordered_nodes_dict().itervalues():
            #print("Node %d" % node.node_id)
            #print("Product name %s" % node.product_name)
        
            if node.isReady and ((node.product_name == "Multi Sensor") or (node.product_name == "MultiSensor 6")):
                values = node.get_values("All","All","All",False,"All")
                for value in values.itervalues():
                    
                    if value.label == "Group 1 Interval":
                        value.data = Grp_interval
                    if value.label == "Group 1 Reports":
                        value.data = Grp_reports                  # Group 1 Reports :  Temperature, Luminance, Humidity and battery
                    if value.label == "Wake-up Interval":
                        value.data = Wakeup_interval
                    #if value.label == "Group 2 Interval":
                    #    value.data = 180
                    #if value.label == "Group 2 Reports":
                    #    value.data = 0
                    #if value.label == "Group 3 Interval":
                    #    value.data = 180
                    #if value.label == "Group 3 Reports":
                    #    value.data = 0
        return "Configuration of sensors : Group 1 Interval = "+str(Grp_interval)+";  Group 1 Reports = "+str(Grp_reports)+";  Wake-on Interval = "+str(Wakeup_interval)








###########################################################################################################################
###########################################################################################################################
##################    Switches class     ##################################################################################
###########################################################################################################################
###########################################################################################################################

class Backend_with_switches(Backend):

    def __init__(self):
        Backend.__init__(self)
    
    def get_switches(self):
        # returns the list of switches
        switches = OrderedDict()
        for node in self.ordered_nodes_dict().iterkeys():
            if self.network.nodes[node].get_switches():
                if self.network.nodes[node].isReady:
                    switches[str(node)] = self.network.nodes[node].product_name
                else:
                    switches[str(node)] = ""
        return jsonify(switches)


    def switch_on(self, name):
        print("Activating switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                for val in node.get_switches():
                    node.set_switch(val, True)

    def switch_off(self, name):
        print("Deactivating switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                for val in node.get_switches():
                    node.set_switch(val, False)

    def get_switch_status(self, name):
        print("Querying switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                state = False
                for val in node.get_switches():
                    state = (state or node.get_switch_state(val))
        return state

    def switch_on1(self, name):
        print("Activating switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                val = node.get_switches().keys()[0]
                node.set_switch(val, True)


    def switch_off1(self, name):
        print("Deactivating switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                val = node.get_switches().keys()[0]
                node.set_switch(val, False)

    def get_switch_status1(self, name):
        print("Querying switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                val = node.get_switches().keys()[0]
                state = node.get_switch_state(val)
        return state

    def switch_on2(self, name):
        print("Activating switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                if  node.get_switches().keys()[1]:
                    val = node.get_switches().keys()[1]
                    node.set_switch(val, True)


    def switch_off2(self, name):
        print("Deactivating switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                if  node.get_switches().keys()[1]:
                    val = node.get_switches().keys()[1]
                    node.set_switch(val, False)

    def get_switch_status2(self, name):
        print("Querying switch %s" % name)
        parsed_id = 0
        try:
            parsed_id = int(name)
        except ValueError:
            pass
        for key, node in self.network.nodes.iteritems():
            if node.name == name or node.node_id == parsed_id:
                if  node.get_switches().keys()[1]:
                    val = node.get_switches().keys()[1]
                    state = node.get_switch_state(val)
                return state





###########################################################################################################################
##################    Dimmers class     ##################################################################################
###########################################################################################################################
###########################################################################################################################

class Backend_with_dimmers(Backend):

    def __init__(self):
        Backend.__init__(self)

    def get_dimmers(self):
        # returns the list of dimmers
        dimmers = OrderedDict()
        for node in self.ordered_nodes_dict().iterkeys():
            if self.network.nodes[node].get_dimmers():
                if self.network.nodes[node].isReady:
                    dimmers[str(node)] = self.network.nodes[node].product_name
                else:
                    dimmers[str(node)] = ""
        return jsonify(dimmers)


    def get_dimmer_level(self, n):
        # sets dimmer's level
        for node in self.ordered_nodes_dict().itervalues():
            if node.node_id == n and n != 1 and node.isReady and node.product_name == "ZE27" :
                values = node.get_values("All","All","All",False,"All")
                for value in values.itervalues():
                    print value.index
                    print value.label
                    print value.data
                    print "------------"

                    if value.label == "Level":
                        val = value.data
                        return jsonify(controller = name, dimmer = node.node_id, location = node.location, type = value.label.lower(), updateTime = self.timestamps["timestamp"+str(node.node_id)], value = val)


    def set_dimmer_level(self, n, level):
        # sets dimmer's level
        for node in self.ordered_nodes_dict().itervalues():
            if node.node_id == n and n != 1 and node.isReady and node.product_name == "ZE27" :
                values = node.get_values("All","All","All",False,"All")
                for value in values.itervalues():
                    if value.label == "Level":
                        value.data = level


###########################################################################################################################
###########################################################################################################################
##########    Switches, Dimmers  and multisensors class         ###########################################################
###########################################################################################################################
###########################################################################################################################

class Backend_with_switches_dimmers_and_sensors(Backend_with_switches, Backend_with_dimmers, Backend_with_sensors): #Cette classe sera utilise dans "flask-main"

    pass





