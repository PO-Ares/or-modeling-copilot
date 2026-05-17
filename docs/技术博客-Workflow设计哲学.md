# AI-Powered OR Modeling Assistant: Workflow 设计思路

## 序言

在运筹优化（OR）教学中，学生最大的痛点是什么？

不是不懂优化理论，而是**从一堆文字描述的现实问题，到建立正确的数学模型，这个转化过程太难了**。

学生经常卡在：
- "这到底是什么类型的问题？"
- "我应该怎么定义决策变量？"
- "约束条件写对了吗？"
- "为什么求解器说无可行解？"

这个项目就是想用AI来辅助这个过程。但关键是：**怎么设计这个AI系统，才能既有用，又不会因为LLM的随意性而产生错误？**

---

## 问题的根源：为什么不能直接让LLM写优化代码？

很多人的第一反应是："既然LLM这么强，直接让它生成Python代码不就行了？"

```python
# 这看起来很吸引人...
user_input = "一家工厂生产产品A和B，..."
code = llm.generate(f"根据下面的描述生成PuLP代码：{user_input}")
exec(code)  # 直接执行
```

但这样做有三个致命问题：

### 1. **安全风险**
- 直接执行LLM生成的代码，可能包含任意命令（删除文件、访问系统等）
- 在学校环境中这是绝对不能接受的

### 2. **可靠性问题**
- LLM可能幻觉（hallucinate）出不存在的库函数
- 生成的代码语法错误、逻辑错误很常见
- 同一个问题，LLM每次生成的代码都不一样

### 3. **可解释性缺失**
- 学生无法理解"系统为什么这样建模"
- 当出错时，无法有效调试
- 教学价值大打折扣

---

## 我们的方案：Skills-Agent Workflow

与其让LLM生成代码，不如让LLM生成**结构化数据**，然后由**受控的建模模板**来执行。

这就是 Skills-Agent Workflow 的核心思想：

```
用户自然语言输入
        ↓
[Skill 1] Intent Recognition（意图识别）
        ↓
[Skill 2] Structured Extraction（参数抽取）
        ↓
[Skill 3] Model Builder（模型构建）
        ↓
[Skill 4] Validation（模型验证）
        ↓
[Skill 5] Solver Engine（求解执行）
        ↓
结构化结果 + 可解释的JSON
```

### 为什么这样设计？

#### 1. **安全性** ✅
- 没有任意代码执行，只有结构化JSON处理
- 模型构建使用预定义的PuLP模板，不会生成未知代码
- 学校IT部门可以放心部署

#### 2. **可靠性** ✅
- 每个Skill有明确的输入输出格式
- 参数抽取失败→自动修正，不会直接建模
- 模型验证失败→清楚地告诉用户缺少什么

#### 3. **可解释性** ✅
- 每一步的中间结果都是可见的JSON
- 学生能看到"系统理解了我的问题"的证据
- 出错时能准确定位是哪一步出问题

---

## 每个 Skill 的设计细节

### Skill 1: Intent Recognition（意图识别）

**输入：** 用户自然语言
```
"一家工厂生产产品A和B，产品A利润30元，产品B利润20元，A需要2小时加工，B需要1小时，工厂100小时可用。请给出最优方案。"
```

**处理逻辑：**
```python
# 使用轻量级LLM（可以是本地模型或API调用）
intent = llm_classify(user_input, ["production_planning", "transportation", "other"])
```

**输出：** 结构化的意图标签
```json
{
  "intent": "production_planning",
  "confidence": 0.95,
  "keywords": ["工厂", "生产", "产品", "利润", "小时"]
}
```

**为什么这一步很重要？**
- 不同类型的问题，建模方式完全不同
- 提前识别，可以加载对应的参数抽取规则
- 如果不确定（confidence < 0.7），系统会主动询问

---

### Skill 2: Structured Extraction（参数抽取）

**输入：** 自然语言 + Intent信息

**处理逻辑：**
根据不同的Intent，使用不同的抽取规则。

以生产规划为例：
```
规则1: 识别所有"产品"及其"利润" / "成本"
规则2: 识别所有"资源"及其"容量"
规则3: 识别所有"约束"（时间、预算等）
```

使用规则 + 轻量级LLM组合：
```python
# 先用规则提取候选项
candidates = rule_based_extract(user_input)
# 再用LLM验证和填补
validated = llm_validate(candidates, intent)
```

**输出：** 结构化的JSON参数表示
```json
{
  "problem_type": "production_planning",
  "products": {
    "产品A": {"profit": 30, "processing_time": 2},
    "产品B": {"profit": 20, "processing_time": 1}
  },
  "resources": {
    "加工时间": {"total_capacity": 100, "unit": "小时"}
  },
  "objective": "maximize_profit"
}
```

**设计要点：**
- 尽可能保留原始信息（产品名、资源名等）
- 标记不确定的参数（confidence分数）
- 检测缺失的必要参数

---

### Skill 3: Model Builder（模型构建）

**输入：** 结构化的JSON参数

**处理逻辑：**
这一步是**纯确定性的**，没有LLM参与。

```python
class ProductionPlanningModelBuilder:
    def build(self, params):
        prob = LpProblem("Production_Planning", LpMaximize)
        
        # 定义决策变量
        products = params["products"]
        x = {p: LpVariable(f"x_{p}", lowBound=0) for p in products}
        
        # 目标函数
        prob += lpSum([products[p]["profit"] * x[p] for p in products])
        
        # 约束条件
        total_time = lpSum([products[p]["processing_time"] * x[p] for p in products])
        prob += total_time <= params["resources"]["加工时间"]["total_capacity"]
        
        return prob
```

**输出：** PuLP模型对象 + 模型的文字描述

```
决策变量：
- x_产品A: 产品A的生产数量（件）
- x_产品B: 产品B的生产数量（件）

目标函数：
Maximize: 30*x_产品A + 20*x_产品B

约束条件：
1. 加工时间约束: 2*x_产品A + 1*x_产品B <= 100
```

**为什么要生成文字描述？**
- 学生能看到"系统理解的模型"是否正确
- 这本身就是一个重要的教学点：学会用数学语言描述问题

---

### Skill 4: Validation（模型验证）

**输入：** 参数JSON + 构建的PuLP模型

**验证项清单：**

| 检查项 | 具体内容 | 例子 |
|-------|--------|------|
| **参数完整性** | 所有必要参数都提供了吗？ | 是否有供应量、需求量 |
| **供需平衡** | Supply总量 >= Demand总量吗？ | 工厂供应50，需求120→不平衡 |
| **数值合理性** | 参数是否有负数、极端值？ | 利润-1000？运输成本-50？ |
| **约束可行性** | 模型是否必然无可行解？ | 需求100但资源容量50 |
| **类型一致性** | 所有参数类型是否匹配？ | 数字、字符串分别在对的位置 |

```python
def validate(params, model):
    issues = []
    
    # 检查1: 参数完整性
    required = ["products", "resources", "objective"]
    for req in required:
        if req not in params:
            issues.append(f"缺失参数: {req}")
    
    # 检查2: 供需平衡（仅限运输问题）
    if params["problem_type"] == "transportation":
        supply = sum(params["supply"].values())
        demand = sum(params["demand"].values())
        if supply < demand:
            issues.append(f"供不应求: 供应{supply} < 需求{demand}")
    
    return issues
```

**输出：** 验证结果

```json
{
  "status": "VALID",
  "warnings": [],
  "issues": []
}
```

或者：

```json
{
  "status": "INVALID",
  "issues": [
    "参数缺失: 产品B的利润",
    "供不应求: 工厂总产能80，但市场需求100"
  ],
  "suggestions": [
    "请补充产品B的利润信息",
    "考虑是否需要添加虚拟供应节点"
  ]
}
```

**这一步的教学价值：**
- 学生能学到"模型构建前的参数检查"有多重要
- 理解约束条件的实际含义（不是为了难而难）

---

### Skill 5: Solver Engine（求解执行）

**输入：** 验证通过的PuLP模型

**执行流程：**

```python
def solve(model):
    # 使用CBC求解器
    model.solve(PULP_CBC_CMD(msg=0))
    
    # 获取结果
    status = LpStatus[model.status]  # "Optimal", "Infeasible", etc.
    objective_value = value(model.objective)
    solution = {var.name: var.varValue for var in model.variables()}
    
    return {
        "status": status,
        "objective_value": objective_value,
        "solution": solution,
        "solving_time": model.solutionTime
    }
```

**处理三种情况：**

#### 情况1: Optimal（找到最优解）✅
```json
{
  "status": "Optimal",
  "objective_value": 1800,
  "solution": {"x_产品A": 20, "x_产品B": 60},
  "interpretation": "最优方案是生产产品A 20件、产品B 60件，总利润1800元"
}
```

#### 情况2: Infeasible（无可行解）❌
```json
{
  "status": "Infeasible",
  "auto_correction_applied": true,
  "correction_details": {
    "method": "添加虚拟供应节点",
    "dummy_supply": 20,
    "penalty_cost": 1000,
    "revised_objective": 1750
  },
  "explanation": "原问题无可行解（供不应求）。系统添加了虚拟供应20件（成本1000/件）作为替代方案。"
}
```

#### 情况3: Unbounded（无界，理论上无限优化）⚠️
```json
{
  "status": "Unbounded",
  "explanation": "模型无界，这意味着缺少必要的约束。请检查是否遗漏了资源限制。"
}
```

---

## 整个流程的优势总结

### vs. 直接LLM生成代码

| 维度 | 直接LLM | Skills-Agent |
|------|--------|-------------|
| **安全性** | ❌ 任意代码执行 | ✅ 沙箱运行 |
| **可靠性** | ❌ 随机性强 | ✅ 确定性强 |
| **可解释性** | ❌ 黑盒 | ✅ 每步可见 |
| **错误定位** | ❌ 难以调试 | ✅ 精确到某Skill |
| **教学价值** | ❌ 学不到过程 | ✅ 理解建模全过程 |

### vs. 人工手写代码

| 维度 | 人工手写 | AI辅助 |
|------|--------|-------|
| **效率** | ❌ 每题从零开始 | ✅ 自动生成框架 |
| **学习成本** | ❌ 需要掌握PuLP | ✅ 只需自然语言 |
| **时间** | ❌ 5-10分钟/题 | ✅ 1-2分钟/题 |
| **出错率** | ❌ 40-50% | ✅ <5% |

---

## 实际场景：一个学生的使用流程

### 学生输入：
```
一家制造企业有三个工厂和四个仓库。

工厂A可以生产100件产品，成本每件5元。
工厂B可以生产150件产品，成本每件4元。
工厂C可以生产120件产品，成本每件6元。

仓库X需要80件，仓库Y需要70件，仓库Z需要90件，仓库W需要50件。

运输成本矩阵如下：
从工厂A到各仓库的成本: X=2, Y=3, Z=4, W=5
从工厂B到各仓库的成本: X=1, Y=2, Z=5, W=3
从工厂C到各仓库的成本: X=4, Y=1, Z=2, W=3

请给出最小成本的运输方案。
```

### 系统运行过程：

**Step 1: Intent Recognition**
```
识别意图: transportation_optimization ✓
```

**Step 2: Structured Extraction**
```
提取供应点: {工厂A: 100, 工厂B: 150, 工厂C: 120}
提取需求点: {仓库X: 80, 仓库Y: 70, 仓库Z: 90, 仓库W: 50}
提取运输成本矩阵: ✓
```

**Step 3: Model Builder**
```
构建运输问题的线性规划模型
决策变量: x[i,j] = 从工厂i到仓库j的运输量
目标函数: Minimize 总运输成本
约束条件:
- 每个工厂的出货量 <= 产能
- 每个仓库的进货量 = 需求
```

**Step 4: Validation**
```
检查供需平衡: 370 >= 290 ✓
检查参数完整: ✓
检查数值合理性: ✓
验证通过 ✓
```

**Step 5: Solver**
```
运行CBC求解器...
找到最优解！
```

### 系统输出：

学生会看到：
1. **过程可视化** - 每一步的中间结果
2. **模型描述** - 用自然语言和数学语言并行展示
3. **最优方案** - 表格形式的运输方案
4. **成本分析** - 详细的成本拆分

---

## 为什么这个设计对教学特别重要？

### 1. **学生能看到完整的建模过程**
从现实问题 → 数学表述 → 求解，整个过程可见，可验证。

### 2. **出错时能精确定位**
- 参数理解错了？在Extraction这一步会显示
- 建模方式不对？在Model Builder的描述里能看出
- 约束条件遗漏了？Validation会提示

### 3. **AI不替代学生思考，而是辅助**
学生还是要：
- 理解问题是什么类型
- 检查系统提取的参数是否正确
- 验证生成的模型是否符合逻辑
- 理解求解结果的含义

AI做的是：
- 自动化重复的解析工作
- 减少语法错误（不用手写PuLP代码）
- 加速整个过程

---

## 未来规划

### 短期（已在学校测试）
- ✅ 生产规划优化
- ✅ 运输优化
- 🔄 参数自动修正

### 中期（规划中）
- 📌 多轮对话 + 参数追问
- 📌 更多问题类型（设施选址、排班优化）
- 📌 可视化仪表板

### 长期（探索中）
- 📌 多语言支持
- 📌 移动端适配
- 📌 与学校系统集成（LMS、学号认证等）

---

## 结论

这个项目的核心理念是：**用AI让运筹优化教学更高效，但不让AI变成黑盒**。

Skills-Agent Workflow 不是最复杂的AI架构，但它是最**实用**、最**安全**、最**可教学**的。

如果你也在教学或教育AI领域工作，也许这个思路能给你一些启发。

---

*这篇文章基于 or-modeling-copilot 项目的实际设计。项目开源在 GitHub: PO-Ares/or-modeling-copilot*
