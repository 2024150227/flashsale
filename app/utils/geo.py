from app.utils.redis_client import redis_client
from typing import List, Tuple, Optional

class GeoService:
    """
    Redis Geo 服务
    用于存储和查询地理位置信息
    """

    def __init__(self, key_prefix: str = "flashsale:geo"):
        self.key_prefix = key_prefix
    #name是Geo集合的名称
    def get_key(self, name: str) -> str:
        """生成完整的 Redis Key"""
        return f"{self.key_prefix}:{name}"

    def add_location(self, name: str, longitude: float, latitude: float, member: str):
        """
        添加地理位置

        Args:
            name: Geo集合名称，举例："warehouses"
            longitude: 经度
            latitude: 纬度
            member: 成员标识（如门店ID、仓库ID）
        """
        key = self.get_key(name)
        redis_client.geoadd(key, (longitude, latitude, member))

    def add_locations_batch(self, name: str, locations: List[Tuple[str, float, float]]):
        """
        批量添加地理位置

        Args:
            name: Geo集合名称，举例："warehouses"
            locations: [(member, longitude, latitude), ...]
        """
        key = self.get_key(name)
        # 转换为GeoADD需要的格式 (lon, lat, member)
        geo_locations = []
        for member, lon, lat in locations:
            geo_locations.append((lon, lat, member))
        if geo_locations:
            redis_client.geoadd(key, tuple(geo_locations))

    def get_position(self, name: str, member: str) -> Optional[Tuple[float, float]]:
        """
        获取成员的坐标

        Args:
            name: Geo集合名称，举例："warehouses"   
            member: 成员标识

        Returns:
            (longitude, latitude) 或 None
        """
        key = self.get_key(name)
        positions = redis_client.geopos(key, member)
        return positions[0] if positions and positions[0] else None

    def get_distance(self, name: str, member1: str, member2: str, unit: str = "km") -> Optional[float]:
        """
        计算两个成员之间的距离

        Args:
            name: Geo集合名称，举例："warehouses"
            member1: 成员1
            member2: 成员2
            unit: 单位 (m/km/ml/ft)

        Returns:
            距离值或None
        """
        key = self.get_key(name)
        return redis_client.geodist(key, member1, member2, unit)

    def get_nearby(self, name: str, longitude: float, latitude: float,
                   radius: float, unit: str = "km", count: int = 10,
                   sort: str = "ASC") -> List[Tuple[str, float]]:
        """
        查询附近的位置

        Args:
            name: Geo集合名称，举例："warehouses"
            longitude: 中心点经度
            latitude: 中心点纬度
            radius: 半径
            unit: 单位 (m/km/ml/ft)
            count: 返回数量
            sort: 排序 ASC/DESC

        Returns:
            [(member, distance), ...]
        """
        key = self.get_key(name)
        result = redis_client.georadius(
            key, longitude, latitude, radius, unit,
            withdist=True, count=count, sort=sort
        )
        return [(item[0], item[1]) for item in result]

    def get_nearby_by_member(self, name: str, member: str,
                              radius: float, unit: str = "km",
                              count: int = 10, sort: str = "ASC") -> List[Tuple[str, float]]:
        """
        以成员为中心查询附近

        Args:
            name: Geo集合名称，举例："warehouses"
            member: 成员标识
            radius: 半径
            unit: 单位
            count: 返回数量
            sort: 排序

        Returns:
            [(member, distance), ...]
        """
        key = self.get_key(name)
        result = redis_client.georadiusbymember(
            key, member, radius, unit,
            withdist=True, count=count, sort=sort
        )
        return [(item[0], item[1]) for item in result]

    def remove_member(self, name: str, *members: str):
        """
        移除成员

        Args:
            name: Geo集合名称，举例："warehouses"
            members: 要移除的成员
        """
        key = self.get_key(name)
        redis_client.zrem(key, *members)

    def get_member_count(self, name: str) -> int:
        """
        获取Geo集合中的成员数量

        Args:
            name: Geo集合名称，举例："warehouses"   

        Returns:
            成员数量
        """
        key = self.get_key(name)
        return redis_client.zcard(key)


# 秒杀场景常用的Geo函数

    #name是Geo集合的名称，用于存储仓库位置
def add_warehouse(warehouse_id: int, longitude: float, latitude: float):
    """添加仓库位置"""
    geo = GeoService()
    geo.add_location("warehouses", longitude, latitude, f"warehouse_{warehouse_id}")

def add_store(store_id: int, longitude: float, latitude: float):
    """添加门店位置"""
    geo = GeoService()
    geo.add_location("stores", longitude, latitude, f"store_{store_id}")

    #name是Geo集合的名称，用于存储仓库位置
def get_nearby_warehouses(longitude: float, latitude: float,
                          radius: float = 100, unit: str = "km") -> List[Tuple[str, float]]:
    """查询附近仓库"""
    geo = GeoService()
    return geo.get_nearby("warehouses", longitude, latitude, radius, unit)

    #name是Geo集合的名称，stores是门店Geo集合的名称
def get_nearby_stores(longitude: float, latitude: float,
                      radius: float = 10, unit: str = "km") -> List[Tuple[str, float]]:
    """查询附近门店"""
    geo = GeoService()
    return geo.get_nearby("stores", longitude, latitude, radius, unit)

def get_delivery_distance(store_id: int, customer_lon: float, customer_lat: float) -> Optional[float]:
    """计算配送距离"""
    geo = GeoService()
    # 先获取门店坐标
    store_pos = geo.get_position("stores", f"store_{store_id}")
    if store_pos:
        # 临时添加用户位置
        temp_key = f"flashsale:geo:temp_delivery_{customer_lon}_{customer_lat}"
        redis_client.geoadd(temp_key, (customer_lon, customer_lat, "customer"))
        redis_client.geoadd(temp_key, (store_pos[0], store_pos[1], "store"))
        distance = redis_client.geodist(temp_key, "customer", "store", "km")
        redis_client.delete(temp_key)
        return distance
    return None
