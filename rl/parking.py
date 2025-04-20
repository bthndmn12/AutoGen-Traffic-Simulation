import numpy as np

class ParkingRL:
    def __init__(self, action_space=2, alfa=None):
        self.action_space = action_space  # 0 = stay parked, 1 = exit
        self.alfa = alfa
        self.generador = np.random.default_rng()
        self.reset()

    def reset(self):
        self.q = np.zeros(self.action_space)  
        self.action_counts = np.zeros(self.action_space) 
        self.steps = 0  
        self.park_duration = 0 # Time a vehicle has been parked

    def choose_action(self, epsilon=0.15):
        if self.generador.random() < epsilon:
            return self.generador.integers(0, len(self.q))  # Explore
        return np.argmax(self.q)  # Exploit

    def step(self, occupancy, capacity):
        action = self.choose_action()
        self.action_counts[action] += 1

        self.park_duration += 1
        is_full = occupancy >= capacity
        min_park_time = 2

        # Action 0: keep vehicle parked
        if action == 0:
            reward = 1 if self.park_duration < min_park_time else -1

        # Action 1: exit attempt
        else:
            if self.park_duration >= min_park_time:
                reward = 5 if is_full else 3  # Much higher reward for exiting
                self.park_duration = 0
            else:
                reward = -2  # Mild penalty for trying to exit too early

        alfa = self.alfa if self.alfa is not None else 1 / self.action_counts[action]
        self.q[action] += alfa * (reward - self.q[action])

        self.steps += 1

        return reward, action
