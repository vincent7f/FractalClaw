# FractalClaw 开发规范

## 架构检查规则 (第一优先级)

在开发任何新模块时，**必须**满足以下 Fractal 架构要求：

### 1. 组件继承

所有核心模块**必须**继承自 Fractal 组件基类：

```python
from fractalclaw.core.component import Component, CompositeComponent, LeafComponent

# 复合组件 (包含子组件)
class MyCompositeComponent(CompositeComponent):
    pass

# 原子组件 (不包含子组件，但可添加接口)
class MyComponent(Component):
    pass

# 叶子组件 (最简单的组件)
class MyLeafComponent(LeafComponent):
    pass
```

**禁止**直接继承 `object` 或其他非 Fractal 基类。

### 2. Fractal 三大核心特性

必须体现以下三大特性：

| 特性 | 实现要求 | 示例 |
|------|----------|------|
| **递归性** | 使用 `add_child()`/`get_child()` 管理层级组件 | `FractalAgent` 包含 `memory`, `planner`, `executor` 等子组件 |
| **反射性** | 实现 `get_attribute()`, `set_attribute()`, `invoke()` | `Component` 基类已提供 |
| **开放性** | 使用 `Membrane` 定制非功能性服务 | 添加 `LifecycleMembrane`, `SecurityMembrane` 等 |

### 3. 生命周期管理

**必须**实现生命周期钩子：

```python
class MyComponent(Component):
    def _on_initialize(self):
        """初始化 - 资源分配"""
        pass
    
    def _on_start(self):
        """启动 - 开始运行"""
        pass
    
    def _on_stop(self):
        """停止 - 清理资源"""
        pass
    
    def _on_destroy(self):
        """销毁 - 完全清理"""
        pass
```

### 4. 接口系统

**必须**定义服务接口和客户端接口：

```python
from fractalclaw.core.component import ServiceInterface, ClientInterface

self.add_interface(ServiceInterface("service_name", [
    "method1", "method2"
]))
self.add_interface(ClientInterface("client_name"))
```

### 5. 绑定机制 (可选)

如需组件间通信，使用 Binding：

```python
from fractalclaw.core.binding import Binding, BindingType

binding = Binding(
    "name",
    source_component, "source_interface",
    target_component, "target_interface",
    BindingType.SYNC
)
self._binding_manager.add_binding(binding)
```

## 代码审查清单

提交代码前检查：

- [ ] 继承自正确的 Fractal 基类
- [ ] 使用 `add_child()` 管理子组件 (如适用)
- [ ] 实现所有生命周期钩子
- [ ] 定义服务/客户端接口
- [ ] 添加类型注解和文档字符串

## 违规示例

```python
# ❌ 错误：直接继承 object
class MyClass:
    pass

# ✅ 正确：继承 Fractal 组件
class MyComponent(Component):
    pass
```

```python
# ❌ 错误：不实现生命周期
class MyComponent(Component):
    pass

# ✅ 正确：实现生命周期
class MyComponent(Component):
    def _on_initialize(self):
        pass
    
    def _on_start(self):
        pass
    
    def _on_stop(self):
        pass
```