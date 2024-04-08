import yaml, re
from pprint import pprint
from collections import OrderedDict
import xmltodict
from pyecore.resources import ResourceSet, URI
import ast


def example_function():
    # Function body
    pass


class ExampleClass:
    def __init__(self):
        # Constructor body
        pass

    def example_method(self):
        # Method body
        pass

    def transform_code(self, code):
        tree = ast.parse(code)
        return tree

    def test_return_type(self) -> str | None:
        hello = message = 'hi'
        return hello

    def test_return_single(self) -> str:
        hello = message = 'hi'
        if hello == 'hi':
            print(hello)
        elif hello == 'hey':
            print(hello)
        fruits = ["apple", "banana", "cherry"]
        for x in fruits:
            if x == "banana":
                break
            print(x)
        i = 1
        while i < 6:
            print(i)
            i += 1
        return hello


test_code = 'hello'
