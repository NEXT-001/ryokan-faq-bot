import pandas as pd
df = pd.read_pickle("data/faq_with_embeddings.pkl")

print(df.columns)  # ['question', 'answer', 'embedding']
print(len(df["embedding"][0]))  # → 1536 であるべき
print(type(df["embedding"][0][0]))  # floatであるべき



