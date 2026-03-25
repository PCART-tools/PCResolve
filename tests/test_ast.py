import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from single_file_analyzer.symbol_table_builder import analyse

def test_1():
    print("测试1：")
    code="""import requests
from flask import Flask
import numpy as np

resp = requests.get("https://example.com")
app = Flask(__name__)
data = np.array([1, 2, 3])"""
    tracer=analyse(code)
    assert tracer.symbols.get_top('app')=='flask'
    assert tracer.symbols.get_top('resp')=='requests'
    assert tracer.symbols.get_top('data')=='numpy'
    print("通过1")
    print()

def test_2():
    print("测试2：")
    code = """import requests as req
from flask import Flask as F
import numpy as np

r = req.get("https://example.com")
app = F(__name__)
arr = np.array([1, 2, 3])"""
    tracer=analyse(code)
    assert tracer.symbols.get_top('r')=='requests'
    assert tracer.symbols.get_top('app')=='flask'
    assert tracer.symbols.get_top('arr')=='numpy'
    print("通过2")
    print()

def run():
    tests=[test_1, test_2]
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"{test.__name__}失败：{e}")
            return False
    print("测试均通过")
    return True

if __name__=='__main__':
    success=run()
    sys.exit(0 if success else 1)