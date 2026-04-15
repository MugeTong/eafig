# Written by Gemini
import pytest
import os
from dataclasses import field
from typing import List
from eafig import Eafig, register_root, register_config
from eafig.state import ConfigState
from omegaconf import DictConfig


@pytest.fixture(autouse=True)
def cleanup():
    # 执行测试前
    yield
    # 执行测试后，强制重置状态，允许下一个测试重新注册 root
    ConfigState._reset()


def test_basic_registration():
    @register_root
    class BasicConfig:
        a: int
        b: str = "default"

    # 测试手动传入参数
    config = BasicConfig(a=10)
    assert config.a == 10
    assert config.b == "default"


def test_frozen_config():
    @register_config(frozen=True)
    class FrozenConfig:
        x: int = 1

    # Frozen 配置不允许在实例化时传入参数
    with pytest.raises(
        TypeError, match="Cannot provide parameters to frozen configuration"
    ):
        FrozenConfig(x=2)


def test_sub_config_loading():
    @register_config(name="sub")
    class SubConfig:
        val: str = "old"

    # 模拟加载了子配置
    ConfigState._loaded_configs = DictConfig({"sub": {"val": "new"}})

    sub = SubConfig()
    assert sub.val == "new"


def test_priority_logic():
    @register_root
    class PriorityConfig:
        p: int = 1

    # 优先级测试: 1. 加载值 > 2. 手动传入的值 > 3. 默认值

    # 情况 A: 只有默认值
    assert PriorityConfig().p == 1

    # 情况 B: 加载值覆盖默认值
    ConfigState._reset()  # 重置状态以允许重新注册 root
    ConfigState._loaded_configs = DictConfig({"p": 2})
    assert PriorityConfig().p == 2

    # 情况 C: 手动传入覆盖加载值
    ConfigState._reset()  # 重置状态以允许重新注册 root
    assert PriorityConfig(p=3).p == 3


def test_list_support(tmp_path):
    # 这里测试你之前关心的 List[str] 是否会导致崩溃
    # 注意：需要确保你的 _convert_type 已经按之前的建议修改过，
    # 否则这个测试会触发你提到的 TypeError
    @register_root
    class ListConfig:
        tags: List[str] = field(default_factory=list)

    # 即使加载的是 tuple 或其他序列，也应尝试转换（或保持）
    ConfigState._loaded_configs = DictConfig({"tags": ["a", "b"]})
    config = ListConfig()
    assert config.tags == ["a", "b"]


def test_save_load_integration(tmp_path):
    @register_root
    class SaveConfig:
        name: str = "test"

    save_path = tmp_path / "config.yaml"

    # 模拟实例化并保存
    instance = SaveConfig(name="exported")
    Eafig.save(str(save_path))

    assert os.path.exists(save_path)
    with open(save_path, "r") as f:
        content = f.read()
        assert "name: exported" in content
