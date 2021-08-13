import random

class PseudoRandomGenerator():

    def __init__(self,step=0.085):
        self.step = step
        self.current_chance = step

    def get_bool(self) -> bool:
        random_num = random.random()
        if random_num < self.current_chance:
            self.current_chance = self.step
            return True
        else:
            self.current_chance += self.step
            return False

