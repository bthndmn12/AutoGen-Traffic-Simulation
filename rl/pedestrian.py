import numpy as np

class PedestrianCrossingRL:
    def __init__(self, action_space=2, alfa=None):
        self.action_space = action_space    # 0 = Pedestrian crossing occupied (stop), 1 = Pedestrian crossing free (continue driving)
        self.alfa = alfa
        self.generador = np.random.default_rng()
        self.reset()

    def reset(self):
        self.q = np.zeros(self.action_space)  
        self.action_counts  = np.zeros(self.action_space) 
        self.steps = 0  
        self.wait_time   = 0   # Time vehicles have been waiting

    def choose_action(self, epsilon=0.1):
        if self.generador.random() < epsilon:
            return self.generador.integers(0, len(self.q))  # Explore
        return np.argmax(self.q)  # Exploit
 
    def step(self, queue_length, road_type):
        action = self.choose_action()
        self.action_counts[action] += 1

        min_wait_time  = 1 if road_type == "1_carril" else 2
        self.wait_time  += 1  

        # Action 0: pedestrian corssing is occupied
        if action == 0:   # Vehicle decides to stop
            if self.wait_time >= min_wait_time :  # Penalize for waiting
                reward = -queue_length  # Allowing crossing after proper wait
                self.wait_time  = 0  # Reset the wait time after stopping for pedestrians
            else: 
                reward = -100  # Strong penalty before the required waiting time
        else: # Action 1: pedestrian crossing is free
            reward = queue_length 

        alfa = self.alfa if self.alfa is not None else 1 / self.action_counts[action]
        self.q[action] += alfa * (reward - self.q[action])

        self.steps += 1

        return reward, action