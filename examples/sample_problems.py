"""Sample problems for the Operations Research Modeling Assistant.

Run this file to print example payloads that can be used in the Streamlit app
or sent to the FastAPI endpoint `/api/pipeline/full`.
"""

SAMPLE_PROBLEMS = {
    "production_planning": """我是一个工厂的计划经理。我们有3条产线，可以生产A、B、C三种产品。
产线1每月产能1000单位，成本100元/单位。
产线2每月产能800单位，成本120元/单位。
产线3每月产能600单位，成本150元/单位。
需求是A产品500单位，B产品400单位，C产品300单位。
请问怎么分配生产才能最小化成本？""",

    "transportation_planning": """我们有3个配送中心，需要给客户组配送商品。
配送中心1库存200件，配送中心2库存150件，配送中心3库存180件。
不同配送中心到不同客户组的单位配送成本不同。
请建立一个运输分配模型，使总配送成本最低。""",

    "portfolio_optimization": """我有100万元需要投资，有4种投资产品：
产品A年化收益10%，风险等级2；产品B年化收益8%，风险等级1；
产品C年化收益12%，风险等级3；产品D年化收益6%，风险等级1。
目标是最大化收益，同时限制平均风险等级不超过2。
请问应该如何分配投资？""",
}


def get_sample_problem(name: str) -> str:
    """Return a sample problem by name."""
    if name not in SAMPLE_PROBLEMS:
        raise KeyError(f"Unknown sample problem: {name}")
    return SAMPLE_PROBLEMS[name]


if __name__ == "__main__":
    for key, problem in SAMPLE_PROBLEMS.items():
        print("=" * 80)
        print(key)
        print("-" * 80)
        print(problem)
