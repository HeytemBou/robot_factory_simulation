
## Installation

1. Clone or download the script:
   ```bash
   git clone git@github.com:HeytemBou/robot_factory_simulation.git
    ```
2. Navigate to the project directory.
3. Run the script:
   ```bash
   python robot_factory.py
   ```
4. Output will be displayed in the terminal, wait for the process to finish, final report will be displayed in the end.

## Design choices

- The implementation is composed of 5 main classes/components : **Robot**, **Task manager**, **Resource manager**, **Activity**, **Production line**.
- **The resource manager** : class that offers a common interface to manage the resources (**foo**, **bar**, **foobar**, **revenue**, **robots**) in a thread safe way, it also notifies the production line when a resource reaches a certain threshold
( e.g when robots count reaches 30 or when a certain resource is scarce and needs to be accumulated)
- **The activity manager** : class that manages the activities and assigns them to robots, each activity execution happens in a separate thread
- **The robot** : class represents the robot that will perform the activities, it has a unique id and a status (idle or busy), Robots 
are assigned activities by the activity manager and through the resource manager they can access the resources to update/consume them.
- **The activity** : class represents the activity that the robot will execute, it has a type, duration, success rate, cost, status and an outcome
- **The production line** : class orchestrates the whole process, it instantiates the activity manager and the resource manager, it initializes the resources and writes to the console.

## Motivation behind these choices : 
- Decouple activity management from resource management.
- Be able to implement notifications through callbacks between different components, most notably between the resource manager and the production line, and between the activity manager and the robots.
- Be able to run activities concurrently, and be able to dynamically adjust the activities based on the current status of the resources.
- Be able to easily extend the implementation by adding new activity types, resources, or robot types.
- Keep the 

## Possible improvements:
- Use a priority queue instead of a normal queue, to be able to compute priority scores for each activity separately (e.g at the start of the production line activities that to accumulate resources should be the priority, minimize activity switching to avoid penalty of switching)
- Update the production line to dynamically adjust the activities based on the current status of the resources (the current implemenation uses static heuristic rules to decide which activity to assign to a robot)
- Use multiprocessing to run the activities in parallel instead of threads
