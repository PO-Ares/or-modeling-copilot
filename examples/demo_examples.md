# Demo Examples

## 1. Transportation allocation with structured parameters

```text
Transportation problem. supply: A=50, B=70; demand: X=30, Y=40, Z=50; cost_matrix=[[2,4,5],[3,1,7]]. Solve min cost.
```

Expected behavior:
- Intent is recognized as `transportation`.
- Supplies, demands, and cost matrix are extracted into `structured_parameters`.
- A PuLP transportation model is generated and solved.

## 2. Production planning

```text
我们有3条产线。产线1每月产能1000单位，成本100元/单位；产线2每月产能800单位，成本120元/单位；产线3每月产能600单位，成本150元/单位。A产品需求500单位，B产品需求400单位，C产品需求300单位。请最小化生产成本。
```

Expected behavior:
- Intent is recognized as `production_planning`.
- Capacity, unit cost, and product demand are extracted when possible.
- A production planning LP is generated.

## 3. Portfolio optimization

```text
我有100万元预算。有4种投资产品：产品A年化收益10%，风险等级2；产品B年化收益8%，风险等级1；产品C年化收益12%，风险等级3；产品D年化收益6%，风险等级1。平均风险等级不超过2，最大化收益。
```

Expected behavior:
- Intent is recognized as `portfolio`.
- Budget, returns, risk levels, and risk limit are extracted.
- A portfolio optimization model is generated.
