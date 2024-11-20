class Memory:
    def __init__(self, k: int = 10):
        self.memory = []
        self.k = k

    def add_message(self, message: str, name: str):
        self.memory.append({
            "name": name,
            "message": message
        });
    
        self.memory = self.memory[-self.k:]

    def get_history(self):
        history = ""
        for message in self.memory:
            history += f"{message['name']}: {message['message']}\n"
        return history
    
    def clear(self):
        self.memory = []