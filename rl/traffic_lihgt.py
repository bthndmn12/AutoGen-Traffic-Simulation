import numpy as np

class TrafficlightRL:
    def __init__(self, action_space=3, alfa=None):
        self.action_space = action_space   # 0 = keep current light, 1 = turn to green, 2 = turn to red
        self.alfa = alfa
        self.generador = np.random.default_rng()
        self.reset()

    def reset(self):
        self.q = np.zeros(self.action_space)  
        self.action_counts = np.zeros(self.action_space)  
        self.steps = 0
        self.green_light_steps = 0  

    def choose_action(self, epsilon=0.1):
        if self.generador.random() < epsilon:
            return self.generador.integers(0, len(self.q))  # Explore
        return np.argmax(self.q)  # Exploit the best action

    def step(self, traffic_light, queue_length):
        action = self.choose_action()
        self.action_counts[action] += 1

        # Actions: 0 = keep current light, 1 = change to green, 2 = change to red
        if action == 1 and traffic_light.state == "RED":
            traffic_light.state = "GREEN" # Change light to green
            self.green_light_steps = 0
        elif action == 2 and traffic_light.state == "GREEN":
            traffic_light.state = "RED" # Change light to red
        elif traffic_light.state == "GREEN":
            self.green_light_steps += 1 # Increment green light step counter

        reward = -queue_length if traffic_light.state == "RED" else queue_length - self.green_light_steps

        alfa = self.alfa if self.alfa is not None else 1 / self.action_counts[action]
        self.q[action] += alfa * (reward - self.q[action])

        self.steps += 1

        return reward, action