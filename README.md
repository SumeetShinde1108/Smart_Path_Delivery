# Smart Path Delivery

# Introduction 
A system for delivering items to multiple locations by determining the shortest possible path that satisfies delivery requirements, ensures all destinations are visited, and returns to the starting point efficiently.


## Branches 
## 1. Setup_feature 
### This branch includes:
    1.All required settings for the project.
    2.Docker system configurations.
    2.The complete project structure for the Smart Path Delivery application.
    

## 2.Model_Feature  
### Models, admin configurations, and utility functions for routing algorithms.
    Brute Force Algorithm: Calculates all possible paths for deliveries.
    Shortest Path Selection: Identifies the most efficient route using the Haversine formula to compute distances between two geographical locations.
    Vehicle Optimization: Allocates vehicles to minimize usage while ensuring deliveries are completed efficiently.

### Models:
 
 #### 1. Location Model
    > Stores location information for:
        1. Customer orders.
        2. Stores or hubs.
        3. Includes geographical coordinates for precise routing.

 #### 2. Order Model
    > Captures details of customer orders, such as:
        1. Order ID.
        2. Items and quantities.

 #### 3. Store Model
    > Represents a hub or warehouse where:
        1. Vehicles begin and end their delivery routes.
        2. Inventory for deliveries is stored.

 #### 4. Vehicle Model
    > Contains details about vehicles, including:
        1. Vehicle number.
        2. Weight capacity.
        3. Average speed.

 #### 5. Delivery Model
    > Tracks delivery-specific details:
        1. Assigned vehicles for the delivery.
        2. Total route distance.
        3. Total weight carried by all vehicles.


