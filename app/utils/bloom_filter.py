import mmh3
from app.utils.redis_client import redis_client

class BloomFilter:
    """
    Redis布隆过滤器实现
    用于高效判断元素是否存在，适合拦截恶意查询
    """

    def __init__(self, key: str, size: int = 1000000, error_rate: float = 0.01):
        """
        初始化布隆过滤器
        
        Args:
            key: Redis键名
            size: 预计元素数量
            error_rate: 误判率（默认0.01）
        """
        self.key = key
        self.size = size
        self.error_rate = error_rate
        
        # 根据误差率和元素数量计算哈希函数个数和位数组大小
        self.num_hashes = self._calculate_num_hashes(size, error_rate)
        self.bit_size = self._calculate_bit_size(size, error_rate)

    def _calculate_num_hashes(self, n: int, p: float) -> int:
        """计算所需哈希函数个数"""
        import math
        return max(1, int(math.ceil(-math.log(p) / math.log(2))))

    def _calculate_bit_size(self, n: int, p: float) -> int:
        """计算位数组大小"""
        import math
        return max(1, int(math.ceil(-n * math.log(p) / (math.log(2) ** 2))))

    def _get_hashes(self, value: str) -> list:
        """获取多个哈希值"""
        hashes = []
        for i in range(self.num_hashes):
            # 使用不同的种子生成不同的哈希值
            hash_value = mmh3.hash(value, i)
            hashes.append(abs(hash_value) % self.bit_size)
        return hashes

    def add(self, value: str):
        """
        添加元素到布隆过滤器
        
        Args:
            value: 要添加的元素（字符串）
        """
        if not isinstance(value, str):
            value = str(value)
        
        hashes = self._get_hashes(value)
        pipe = redis_client.pipeline()
        for h in hashes:
            pipe.setbit(self.key, h, 1)
        pipe.execute()

    def add_batch(self, values: list):
        """
        批量添加元素
        
        Args:
            values: 元素列表
        """
        pipe = redis_client.pipeline()
        for value in values:
            if not isinstance(value, str):
                value = str(value)
            hashes = self._get_hashes(value)
            for h in hashes:
                pipe.setbit(self.key, h, 1)
        pipe.execute()

    def contains(self, value: str) -> bool:
        """
        判断元素是否存在（可能有false positive）
        
        Args:
            value: 要检查的元素
        
        Returns:
            False: 元素一定不存在
            True: 元素可能存在（有一定误判率）
        """
        if not isinstance(value, str):
            value = str(value)
        
        hashes = self._get_hashes(value)
        for h in hashes:
            if redis_client.getbit(self.key, h) == 0:
                return False
        return True

    def clear(self):
        """清空布隆过滤器"""
        redis_client.delete(self.key)

    def get_stats(self) -> dict:
        """获取布隆过滤器统计信息"""
        bit_count = redis_client.bitcount(self.key)
        return {
            'key': self.key,
            'size': self.size,
            'error_rate': self.error_rate,
            'num_hashes': self.num_hashes,
            'bit_size': self.bit_size,
            'bits_set': bit_count,
            'fill_rate': bit_count / self.bit_size if self.bit_size > 0 else 0
        }


# 秒杀场景常用的布隆过滤器

# 商品ID过滤器 - 用于拦截不存在的商品查询
product_bloom = BloomFilter(
    key="flashsale:bloom:products",
    size=100000,  # 预计10万个商品
    error_rate=0.01  # 1%误判率
)

# 用户ID过滤器 - 用于拦截非法用户
user_bloom = BloomFilter(
    key="flashsale:bloom:users",
    size=1000000,  # 预计100万用户
    error_rate=0.01
)


def init_product_bloom(products: list):
    """
    初始化商品布隆过滤器
    
    Args:
        products: 商品ID列表
    """
    product_bloom.clear()
    product_bloom.add_batch([str(p['id']) for p in products])
    print(f"✅ 商品布隆过滤器已初始化，共 {len(products)} 个商品")


def is_product_exists(product_id: int) -> bool:
    """
    检查商品是否存在（快速判断）
    
    Args:
        product_id: 商品ID
    
    Returns:
        False: 商品一定不存在
        True: 商品可能存在
    """
    return product_bloom.contains(str(product_id))


def is_user_exists(user_id: int) -> bool:
    """
    检查用户是否存在（快速判断）
    
    Args:
        user_id: 用户ID
    
    Returns:
        False: 用户一定不存在
        True: 用户可能存在
    """
    return user_bloom.contains(str(user_id))


def add_user_to_bloom(user_id: int):
    """
    添加用户到布隆过滤器
    
    Args:
        user_id: 用户ID
    """
    user_bloom.add(str(user_id))
