import random
from enum import Enum
from queue import Queue, PriorityQueue
from typing import Optional
from time import sleep
import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def time_converter(real_life_seconds: int) -> float:
    """
    This method converts real life seconds to robot seconds, 1 second for a robot is 5 times shorter than real life
    """
    return real_life_seconds / 5


class ActivityType(Enum):
    """
    Enum class for the activity types
    """
    MINE_FOO = "mine_foo"
    MINE_BAR = "mine_bar"
    ASSEMBLE_FOOBAR = "assemble_foobar"
    BUY_ROBOT = "buy_robot"
    SELL_FOOBAR = "sell_foobar"
    SWITCH_ACTIVITY = "switch_activity"


class ActivityStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Activity:
    """
    Activity class with task type, duration, success rate and cost
    Possible task types: mine_foo, mine_bar, assemble_foobar, buy_robot, sell foobar, switch_activity
    """

    def __init__(self, id: str = None, activity_type: ActivityType = None, activity_status: ActivityStatus = None, duration: int = 0, success_rate: int = 100, cost: dict[str, int] = None, successful_outcome: bool = False):
        self.id = id or str(uuid.uuid4())
        self.activity_type = activity_type
        self.duration = duration
        self.cost = cost
        self.success_rate = success_rate
        self.activity_status = activity_status
        self.successful_outcome = successful_outcome


class Robot:
    """
    Robot class with multiple execute methods
    """

    def __init__(self, id: str = None, is_idle: bool = True, activity_manager=None, last_activity: ActivityType = None, notify_activity_manager_callback: callable = None):
        self.id = id or str(uuid.uuid4())
        self.is_idle = is_idle
        self.activity_manager = activity_manager
        self.last_activity = last_activity
        self.notify_activity_manager_callback = notify_activity_manager_callback
        self.lock = threading.Lock()

    def execute_activity(self, activity: Activity):
        """
        This method is checks if the activity type is supported by the current robot instance and then executes it, returns the result of the activity.
        """
        with self.lock:
            # Update robot status, render it busy
            self.is_idle = False

        if getattr(self, activity.activity_type.value):

            # First check if the robot needs to switch activity
            if self.last_activity and self.last_activity != activity.activity_type:
                self.switch_activity(activity)

            # First consume the duration of the activity and update the status of the activity
            activity.activity_status = ActivityStatus.IN_PROGRESS
            sleep(time_converter(activity.duration))

            # Decide if the task is successful or not based on the success rate
            activity_success = random.choices([True, False], weights=[activity.success_rate, 100 - activity.success_rate], k=1)[0]
            # Update the outcome of the activity
            activity.successful_outcome = activity_success

            # Execute the activity and get the result
            resource_update = getattr(self, activity.activity_type.value)(activity)
            activity.activity_status = ActivityStatus.FINISHED

            # Render the robot idle
            self.is_idle = True

            if self.notify_activity_manager_callback:
                self.notify_activity_manager_callback(self)

            # Return the result of the task
            return resource_update
        else:
            print(f"Task type {activity.activity_type} not supported by robot {self.id}")

    def switch_activity(self, activity):
        """
        Switch activity, consumes 5 seconds
        """
        # Consume 5 seconds
        sleep(time_converter(5))
        # Update the last activity
        self.last_activity = activity.activity_type

    def mine_foo(self, activity):
        """
        Occupy the robot for 1 second and mines 1 foo
        """
        # If the task is successful, update the resources with newly mined foo
        return {"resources_to_add": {
            "foo": 1
        }} if activity.successful_outcome else {}

    def mine_bar(self, activity) -> dict:
        """
        Occupy the robot for 2 seconds and mines 1 bar
        """
        # If the task is successful, return the bar mined
        return {"resources_to_add": {
            "bar": 1
        }} if activity.successful_outcome else {"bar": 0}

    def assemble_foobar(self, activity):
        """
        - Since it takes 10s to sell 5 foobar then we assume it takes 2s to sell 1 foobar
        """
        return {"resources_to_add": {
            "foobar": 1
        },
            "resources_to_consume": {
                **activity.cost
            }} if activity.successful_outcome else {"resources_to_consume": {"foo": activity.cost.get("foo")}}

    def sell_foobar(self, activity):
        """
        Selling a foobar, costs 1 foobar and earns 1 unit of revenue
        """
        return {"resources_to_add": {
            "revenue": 1
        },
            "resources_to_consume": {
                **activity.cost
            }} if activity.successful_outcome else {}

    def buy_robot(self, activity):
        """
        Buy a robot, costs 3 units of revenue and 6 foo
        """
        return {"resources_to_add": {
            "robots": [Robot()]
        },
            "resources_to_consume": {
                **activity.cost
            }} if activity.successful_outcome else {}


class ResourceManager:
    """
    This class is responsible for providing an interface to manage resources
    """
    def __init__(self, resources: Optional[dict], notify_production_callback: callable = None):
        self.resources = resources if resources else {"foo": 0, "bar": 0, "foobar": 0, "robots": [], "revenue": 0}
        self.notify_production_callback = notify_production_callback
        self.lock = threading.Lock()
        self.total_resources_gathered = {"foo": 0, "bar": 0, "foobar": 0, "robots": 0, "revenue": 0}

    def get_resources_status(self) -> dict:
        """
        Return a copy of the current resource status, with robots count instead of list
        """
        resources_copy = self.resources.copy()
        resources_copy["robots"] = len(resources_copy.get("robots"))
        return resources_copy

    def get_resource_status(self, resource: str) -> int:
        """
        Return the quantity of a specific resource
        """
        return self.resources.get(resource)

    def update_resources(self, resources_to_update: dict[str, dict]) -> bool:
        """
        Update the resources with the provided resources
        """
        if resources_to_update:
            with self.lock:
                if "resources_to_add" in resources_to_update:
                    resources_to_add = resources_to_update.get("resources_to_add")
                    for resource in resources_to_add:
                        if resource in self.resources:
                            if resource == "robots":
                                self.resources[resource].extend(resources_to_add.get(resource))
                            else:
                                self.resources[resource] += resources_to_add.get(resource)

                    # Update the total resources gathered
                    for resource in self.total_resources_gathered:
                        if resource in resources_to_add:
                            if resource == "robots":
                                self.total_resources_gathered[resource] += len(resources_to_add.get(resource))
                            else:
                                self.total_resources_gathered[resource] += resources_to_add.get(resource)

                if "resources_to_consume" in resources_to_update:
                    resources_to_consume = resources_to_update.get("resources_to_consume")
                    for resource in resources_to_consume:
                        if resource in self.resources:
                            # Check if the resource quantity is enough to consume
                            if self.resources[resource] >= resources_to_consume[resource]:
                                self.resources[resource] -= resources_to_consume[resource]
                            else:
                                # print(f"Resource {resource} is not enough to consume")
                                return False

        # Check if we reached the objective so we can halt the production
        if self.notify_production_callback and len(self.get_resource_status("robots")) >= 30:
            self.notify_production_callback()

        return True

    def get_an_idle_robots(self, last_activity: ActivityType = None, activity_manager_callback: callable = None) -> Optional[list[Robot]]:
        """
        Get an idle robot, prioritize the robot that has the same last activity to avoid switching activities penalty
        """
        idle_robots = []
        with self.lock:
            for robot in self.resources.get("robots"):
                if robot.is_idle:
                    robot.notify_activity_manager_callback = activity_manager_callback
                    idle_robots.append(robot)
        return idle_robots


class ActivityManager:
    """
    Activity manager responsible for initializing and updating the activity queue
    """

    def __init__(self, resource_manager: ResourceManager):
        self.pending_activities_queue = Queue()
        self.finished_activities_queue = Queue()
        self.resource_manager = resource_manager
        self.lock = threading.Lock()

    def create_new_activity(self, new_activity: Activity) -> None:
        """
        Create a new activity and push it to the pending activities queue
        """
        self.pending_activities_queue.put(new_activity)

    def assign_activity_to_robot(self, robot):
        """
        Assign an activity to a robot
        """
        # First check if we have pending activities in the queue
        if not self.pending_activities_queue.empty():

            # Get the first pending activity from the queue
            activity = self.pending_activities_queue.get()
            # Execute the activity
            resources_to_update = robot.execute_activity(activity)

            # Update the resources
            updated = self.resource_manager.update_resources(resources_to_update)
            if not updated:
                # Update the activity status
                activity.successful_outcome = False

            # Update the activity status
            activity.activity_status = ActivityStatus.FINISHED
            self.finished_activities_queue.put(activity)
        else:
            pass
            #print("No pending activities in the queue")

    def get_activities_status(self):
        """
        Return the number of activities per queue, group them by type
        """
        status = {
            "pending": self.pending_activities_queue.qsize(),
            "finished": self.finished_activities_queue.qsize()
        }
        return status

    def assign_activity_to_idle_robot(self, robot):
        """
        Callback function to assign an activity to an idle robot
        """
        self.assign_activity_to_robot(robot)


class ProductionLine:
    """
    Production line class responsible for managing the whole production process and coordinating between the resource manager and the activity manager
    """

    def __init__(self, resources: Optional[dict] = None, objective_met: bool = False, nb_robots: int = 2):
        self.objective_met = objective_met
        # Initialize the resources
        self.resources = resources or {
            "foo": 0,
            "bar": 0,
            "foobar": 0,
            "robots": [Robot() for _ in range(nb_robots)],
            "revenue": 0
        }

        # Initialize the resource manager
        self.resource_manager = ResourceManager(self.resources, self.halt_production)

        # Initialize the task manager
        self.activity_manager = ActivityManager(self.resource_manager)

    def compute_activity_priority_revised(self) -> list[Activity]:
        activities_to_push = []
        current_resources = self.resource_manager.get_resources_status()
        pending_activities = self.activity_manager.get_activities_status().get("pending", 0)
        available_robots = len([robot for robot in self.resource_manager.resources["robots"] if robot.is_idle])

        # If enough tasks are already pending to keep robots busy, avoid adding more
        if pending_activities >= available_robots:
            print(f"Skipping task creation, pending tasks ({pending_activities}) exceed available non-idle robots ({available_robots})")
            return activities_to_push

        foo_count = current_resources.get("foo", 0)
        bar_count = current_resources.get("bar", 0)
        foobar_count = current_resources.get("foobar", 0)
        revenue = current_resources.get("revenue", 0)

        # Buying robots
        if revenue >= 3 and foo_count >= 6:
            activities_to_push.append(
                Activity(activity_type=ActivityType.BUY_ROBOT, duration=1, cost={"revenue": 3, "foo": 6})
            )

        # Mining tasks
        if foo_count < 20:
            activities_to_push.extend(
                [Activity(activity_type=ActivityType.MINE_FOO, duration=1) for _ in range(5)]
            )

        if bar_count < 10:
            activities_to_push.extend(
                [Activity(activity_type=ActivityType.MINE_BAR, duration=round(random.uniform(0.5, 2))) for _ in range(5)]
            )

        # Assembling tasks
        if foo_count >= 1 and bar_count >= 1:
            max_assemble = min(foo_count//2, bar_count//2)
            activities_to_push.extend(
                [Activity(activity_type=ActivityType.ASSEMBLE_FOOBAR, duration=2, cost={"foo": 1, "bar": 1}, success_rate=60)
                 for _ in range(max_assemble)]
            )

        # Selling tasks
        if foobar_count >= 5:
            activities_to_push.extend(
                [Activity(activity_type=ActivityType.SELL_FOOBAR, duration=2, cost={"foobar": 1})
                 for _ in range(foobar_count // 5)]
            )

        return activities_to_push

    def full_report(self, nb_iterations: int):
        """
        Print a full report of the production line initial resource status and final status, the report includes:
        - Number of robots
        - Number of foo mined
        - Number of bar mined
        - Number of foobar assembled
        - Revenue generated
        - Number of iterations
        - Number of activities executed
        - Number of activities pending
        - Number of activities finished
        - Number of activities failed
        - Number of activities successful
        """
        final_resources = self.resource_manager.total_resources_gathered
        print(f"Number of robots: ", self.resource_manager.get_resources_status().get("robots"))
        print(f"Total number of foo mined: ", final_resources.get("foo", 0))
        print(f"Total number of bar mined: ", final_resources.get("bar", 0))
        print(f"Total number of foobar assembled: ", final_resources.get("foobar", 0))
        print(f"Total Revenue: ", final_resources.get("revenue", 0))
        print(f"Number of iterations: ", nb_iterations)
        activities_status = self.activity_manager.get_activities_status()
        print(f"Number of activities executed: ", activities_status.get("finished", 0))
        print(f"Number of activities pending: ", activities_status.get("pending", 0))
        print(f"Number of activities finished: ", activities_status.get("finished", 0))
        print(f"Number of activities failed: ", activities_status.get("failed", 0))
        print(f"Number of activities successful: ", activities_status.get("finished", 0) - activities_status.get("failed", 0))

    def start_production(self):
        print("------------------------------------------------------------------------------------------------------------------------------------")
        print("-----------------------------------------------------Starting production------------------------------------------------------------")
        print("------------------------------------------------------------------------------------------------------------------------------------")
        print(f"---- Initial resources status ----")
        print(f"Number of robots: ", self.resource_manager.get_resources_status().get("robots"))
        print(f"Number of foo mined: ", self.resource_manager.get_resources_status().get("foo", 0))
        print(f"Number of bar mined: ", self.resource_manager.get_resources_status().get("bar", 0))
        print(f"Number of foobar assembled: ", self.resource_manager.get_resources_status().get("foobar", 0))
        print(f"Revenue: ", self.resource_manager.get_resources_status().get("revenue", 0))

        nb_iterations = 0
        robots_per_activity = {}  # Keep track of the number of activities executed by each robot

        while not self.objective_met:
            nb_iterations += 1
            print(f"===============> Starting iteration {nb_iterations}")
            print(f"===============> Creating activities")

            # Push tasks to the activity queue based on priorities
            activities_to_push = self.compute_activity_priority_revised()
            for activity in activities_to_push:
                self.activity_manager.create_new_activity(activity)

            with ThreadPoolExecutor(max_workers=len(self.resource_manager.get_resource_status("robots"))) as executor:
                print(f"===============> Assigning activities to robots")
                futures = []

                # get idle robots
                robots = self.resource_manager.get_an_idle_robots()
                for robot in robots:

                    # update robot activity count
                    if robot.id not in robots_per_activity:
                        robots_per_activity[robot.id] = 0
                    else:
                        robots_per_activity[robot.id] += 1

                    # Assign a task to the idle robot
                    futures.append(executor.submit(self.activity_manager.assign_activity_to_robot, robot))

                # Process task completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error during task execution: {e}")

        print(f"-------------------------------- Final resources status --------------------------------")
        self.full_report(nb_iterations)
        print(f"-------------------------------- Robots activity count  --------------------------------")
        for robot_id, activity_count in robots_per_activity.items():
            print(f"Robot {robot_id} executed {activity_count} activities")

    def halt_production(self):
        """
        Callback function to stop the production line when the objective is met (robots count reaches 30), should only be called by the resource manager
        """
        self.objective_met = True


############### Running the simulation ####################
if __name__ == "__main__":
    production_line = ProductionLine()
    t1 = time.time()
    production_line.start_production()
    t2 = time.time()
    print(f"Production has taken: {round(t2-t1)} seconds")
