"""LangGraph Agent 编排模块"""

import os
import sys

# 确保 backend/ 在路径中，让所有子模块都能 from app.* import
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/app/graph/
_BACKEND_DIR = os.path.dirname(_THIS_DIR)  # backend/app/
_PROJECT_DIR = os.path.dirname(_BACKEND_DIR)  # backend/
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)