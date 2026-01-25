import pandas as pd
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, answer_similarity

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper


df = pd.read_excel("ragg.xlsx")


df = df.rename(columns={"ground truth": "ground_truth"})

df = df.dropna(subset=["question", "answer", "context", "ground_truth"]).copy()
df["question"] = df["question"].astype(str)
df["answer"] = df["answer"].astype(str)
df["context"] = df["context"].astype(str)
df["ground_truth"] = df["ground_truth"].astype(str)


SEP = "\n\n---\n\n"  
df["contexts"] = df["context"].apply(lambda x: [c.strip() for c in x.split(SEP) if c.strip()])


df = df[df["contexts"].apply(len) > 0].copy()

ds = Dataset.from_pandas(df[["question", "answer", "contexts", "ground_truth"]])

llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0, n=1))
embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

results = evaluate(
    ds,
    metrics=[faithfulness, answer_relevancy, answer_similarity],
    llm=llm,
    embeddings=embeddings,
)

res_df = results.to_pandas()
print(res_df.describe())

out = pd.concat([df.reset_index(drop=True), res_df], axis=1)
out.to_excel("ragas_eval_output.xlsx", index=False)
print("Saved: ragas_eval_output.xlsx")