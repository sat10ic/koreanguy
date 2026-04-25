import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

class Config(dict):
    def __getattr__(self, name):
        if name in self:
            val = self[name]
            if isinstance(val, dict):
                return Config(val)
            return val
        raise AttributeError(f"No such attribute: {name}")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        data = yaml.safe_load(f)
    return Config(data)

if __name__ == '__main__':
    c = load_config()
    print(c)
