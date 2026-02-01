from score_service import engine
import pandas as pd

df = pd.read_sql("SELECT * FROM fund_features LIMIT 0", engine)
print("Columns in fund_features:", df.columns.tolist())

df2 = pd.read_sql("SELECT * FROM funds LIMIT 0", engine)
print("Columns in funds:", df2.columns.tolist())
