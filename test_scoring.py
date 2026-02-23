from score_service import load_latest_features, compute_scores, engine
import warnings
warnings.filterwarnings('ignore')

df = load_latest_features(engine)
scored = compute_scores(df, {})

cols = ['fund_name', 'category', 'ConsistencyScore', 'score_mom', 'Tier']
top = scored[cols].head(15)

print(f"Funds scored: {len(scored)}")
print("\n=== TOP 15 FUNDS AFTER SCORING FIX ===")
for _, r in top.iterrows():
    print(f"[{r['Tier']:<20}] {r['ConsistencyScore']:.1f}  mom={r['score_mom']:.2f}  {r['category']:<20}  {r['fund_name']}")
