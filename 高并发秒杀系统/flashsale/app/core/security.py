from typing import Optional

# 简单的鉴权功能
def verify_user(user_id: int) -> bool:
    """验证用户是否合法"""
    # 这里可以根据实际需求实现更复杂的鉴权逻辑
    return user_id > 0