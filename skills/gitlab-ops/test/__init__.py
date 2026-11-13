"""让 `python -m unittest test.test_xxx`（技能根目录）与 `cd test && python -m unittest test_xxx` 都能运行。

各测试模块用扁平写法 `from conftest import ...`，需本目录在 sys.path 中。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
