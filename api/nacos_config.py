import logging
import os
import yaml
from typing import Dict, Any, Optional
from nacos import NacosClient


class NacosConfigManager:
    """
    Nacos配置管理器，用于从Nacos获取配置并注册服务
    """
    
    def __init__(self, server_addresses: str = None, namespace: str = None):
        """
        初始化Nacos配置管理器
        
        Args:
            server_addresses: Nacos服务器地址，格式为 "host:port[,host:port...]"
            namespace: Nacos命名空间
        """
        self.server_addresses = server_addresses or os.getenv("NACOS_SERVER_ADDRESSES", "127.0.0.1:8848")
        self.namespace = namespace or os.getenv("NACOS_NAMESPACE", "")
        
        # 从环境变量获取Nacos认证信息
        self.username = os.getenv("NACOS_USERNAME")
        self.password = os.getenv("NACOS_PASSWORD")
        
        # 创建Nacos客户端
        self.client = NacosClient(
            server_addresses=self.server_addresses,
            namespace=self.namespace,
            username=self.username,
            password=self.password
        )
        
        self.config_cache = {}
        self.service_name = os.getenv("SERVICE_NAME", "ragflow-plus")
        self.group = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")
        self.service_port = int(os.getenv("HOST_PORT", "9380"))
        self.service_host = os.getenv("HOST_IP", "127.0.0.1")

    def get_config(self, data_id: str, group: str = "DEFAULT_GROUP", timeout_ms: int = 3000) -> Optional[str]:
        """
        从Nacos获取配置
        
        Args:
            data_id: 配置的dataId
            group: 配置的group
            timeout_ms: 超时时间(毫秒)
            
        Returns:
            配置内容字符串，如果获取失败返回None
        """
        try:
            config = self.client.get_config(data_id, group, timeout_ms)
            if config:
                self.config_cache[f"{group}:{data_id}"] = config
            return config
        except Exception as e:
            logging.error(f"Failed to get config from Nacos: {e}")
            return None

    def get_yaml_config(self, data_id: str, group: str = "DEFAULT_GROUP") -> Dict[str, Any]:
        """
        从Nacos获取YAML格式的配置
        
        Args:
            data_id: 配置的dataId
            group: 配置的group
            
        Returns:
            解析后的字典配置
        """
        config_str = self.get_config(data_id, group)
        if config_str:
            try:
                return yaml.safe_load(config_str)
            except yaml.YAMLError as e:
                logging.error(f"Failed to parse YAML config: {e}")
                return {}
        return {}

    def listen_config(self, data_id: str, group: str = "DEFAULT_GROUP", cb=None):
        """
        监听Nacos配置变更
        
        Args:
            data_id: 配置的dataId
            group: 配置的group
            cb: 配置变更回调函数
        """
        try:
            self.client.add_config_watcher(data_id, group, cb)
        except Exception as e:
            logging.error(f"Failed to listen config: {e}")

    def register_service(self, service_name: str = None, group: str = None, 
                        port: int = None, host: str = None, weight: float = 1.0):
        """
        向Nacos注册服务
        
        Args:
            service_name: 服务名称
            group: 服务组
            port: 服务端口
            host: 服务主机
            weight: 服务权重
        """
        service_name = service_name or self.service_name
        group = group or self.group
        port = port or self.service_port
        host = host or self.service_host
        
        try:
            self.client.add_naming_instance(
                service_name=service_name,
                ip=host,
                port=port,
                weight=weight,
                group_name=group,
                cluster_name="DEFAULT",
                enable=True,
                healthy=True
            )
            logging.info(f"Service {service_name} registered successfully at {host}:{port}")
        except Exception as e:
            logging.error(f"Failed to register service: {e}")

    def deregister_service(self, service_name: str = None, group: str = None, 
                          port: int = None, host: str = None):
        """
        从Nacos注销服务
        
        Args:
            service_name: 服务名称
            group: 服务组
            port: 服务端口
            host: 服务主机
        """
        service_name = service_name or self.service_name
        group = group or self.group
        port = port or self.service_port
        host = host or self.service_host
        
        try:
            self.client.remove_naming_instance(
                service_name=service_name,
                ip=host,
                port=port,
                group_name=group,
                cluster_name="DEFAULT"
            )
            logging.info(f"Service {service_name} deregistered successfully")
        except Exception as e:
            logging.error(f"Failed to deregister service: {e}")

    def get_service_instances(self, service_name: str, group: str = "DEFAULT_GROUP"):
        """
        获取服务实例列表
        
        Args:
            service_name: 服务名称
            group: 服务组
            
        Returns:
            服务实例列表
        """
        try:
            return self.client.list_naming_instances(
                service_name=service_name,
                group_name=group,
                cluster="DEFAULT"
            )
        except Exception as e:
            logging.error(f"Failed to get service instances: {e}")
            return []


# 全局配置管理器实例
nacos_config_manager = None


def get_nacos_config_manager() -> NacosConfigManager:
    """
    获取Nacos配置管理器单例
    
    Returns:
        NacosConfigManager实例
    """
    global nacos_config_manager
    if nacos_config_manager is None:
        nacos_config_manager = NacosConfigManager()
    return nacos_config_manager